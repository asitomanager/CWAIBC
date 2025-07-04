"""
This module provides functionality for connecting to and interacting with OpenAI's API.
It includes the OpenAIOrchestrator class which manages real-time conversations,
handles WebSocket connections, and provides methods for text-to-speech and speech-to-text
conversions using OpenAI's models.
"""

import asyncio
import base64
import io
import json
import os
import threading
import wave

import websocket
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from openai import APIConnectionError, APIError, OpenAI
from pydub import AudioSegment

from commons import ConfigLoader, logger

load_dotenv(override=True)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY!")


class OpenAIOrchestrator:
    """A class used to connect to the OpenAI API and manage interactions with the LLM."""

    __CONFIG_PATH = os.path.join("commons", "config.jsonc")

    def __init__(self, instructions: str, fe_websocket: WebSocket):
        self.instructions = instructions
        self.__config = ConfigLoader.get_config(self.__CONFIG_PATH)
        self.__ws = None
        self.__done_event = threading.Event()
        self.fe_websocket = fe_websocket
        self.__client = OpenAI()
        self.text_queue = asyncio.Queue()
        self.audio_queue = asyncio.Queue()

        self.message_processor = asyncio.create_task(self.process_text_queue())
        self.audio_processor = asyncio.create_task(self.process_audio_queue())

        self.transcript = []

    def __on_open(self, _ws):
        """
        input_audio_format (str) [Optional]: The format of the input audio. Defaults to 'pcm16'.
        Formats include 'pcm16', 'g711_ulaw', or 'g711_alaw'.
        For 'pcm16', the audio must be 16-bit PCM at a 24kHz sample rate,
        single channel (mono), and in little-endian byte order.
        """
        logger.info("Connected to %s model!", self.__config["interview_model"])
        session_update_event = {
            "type": "session.update",
            "session": {
                "instructions": self.instructions,
                "temperature": 0.8,
                "modalities": ["audio", "text"],
                "input_audio_transcription": {"model": "whisper-1"},
                # "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    # "threshold": 0.5,
                    # "prefix_padding_ms": 300,
                    "silence_duration_ms": 1000,
                    # "create_response": true
                },
            },
        }
        self.__ws.send(json.dumps(session_update_event))
        logger.debug("Session update sent with default instructions.")
        self.__create_response_event()

    def __create_response_event(self):
        """Send a response creation event requesting text+audio output."""
        event = {"type": "response.create"}
        if self.__ws.sock and self.__ws.sock.connected:
            self.__ws.send(json.dumps(event))
            logger.debug("Requested response from AI.")
        else:
            logger.error("WebSocket connection is closed. Cannot send message.")

    async def __on_message(self, message):
        if self.fe_websocket.client_state != WebSocketState.CONNECTED:
            logger.error("Frontend WebSocket is closed! Cannot send response.")
            return
        response_data = json.loads(message)
        msg_type = response_data.get("type")

        if msg_type == "response.audio.delta":
            audio_chunk = base64.b64decode(response_data.get("delta", ""))
            await self.audio_queue.put(self.__pcm16_to_wav_bytes(audio_chunk))

        elif msg_type == "response.audio_transcript.delta":
            delta_text = response_data.get("delta", "")
            await self.text_queue.put(delta_text)
            logger.debug("Added text '%s' to queue", delta_text)

        elif msg_type == "response.done":
            logger.info("Response complete.")
            gpt_response = response_data.get("response", {})["output"]
            if gpt_response:
                await self.text_queue.put("END_QUESTION")
                try:
                    agent_text = response_data.get("response", {})["output"][0][
                        "content"
                    ][0]["transcript"]
                    self.transcript.append(f"Agent: {agent_text}")
                except Exception as e:
                    logger.error("Error getting agent text: %s", e)
            else:
                logger.error("AI Response is empty.")

            self.__done_event.set()
        elif msg_type == "error":
            logger.error("Received error: %s", response_data)
            self.__done_event.set()

        elif msg_type == "conversation.item.input_audio_transcription.completed":
            self.transcript.append(f"Candidate: {response_data.get("transcript")}")
        else:
            logger.debug("Received: %s", msg_type)
            # print(response_data)

    def stop_conversation(self):
        """
        Stop the conversation and close the WebSocket and OpenAI client connections.

        This method closes the WebSocket connection and the OpenAI client connection,
        and sets the done event to indicate that the conversation is over.

        Returns:
            None
        """
        if hasattr(self, "audio_processor") and not self.audio_processor.done():
            self.audio_processor.cancel()
        if hasattr(self, "message_processor") and not self.message_processor.done():
            self.message_processor.cancel()

        if self.__ws is None:
            logger.warning("WebSocket is already closed or not initialized.")
            return
        try:
            self.__ws.close()
            logger.info("WebSocket connection closed.")
        except websocket.WebSocketException as e:
            logger.error("WebSocket error: %s", str(e))
        finally:
            self.__done_event.set()  # Set the event to indicate that the conversation is over
        if self.__client is not None:
            try:
                self.__client.close()
                logger.info("OpenAI client connection closed.")
            except (APIError, APIConnectionError) as e:
                logger.error("Error closing OpenAI client: %s", str(e))

    def __del__(self):
        self.stop_conversation()

    def __on_error(self, _ws, error):
        logger.error("WebSocket error: %s", error)

    def __on_close(self, _ws, close_status_code, close_msg):
        logger.info("WebSocket closed: %s %s", close_status_code, close_msg)

    def __on_message_wrapper(self, _ws, message):
        # This is a synchronous wrapper for the async method
        asyncio.run(self.__on_message(message))

    async def start_conversation(self):
        """
        Initiates a conversation with the OpenAI API in real-time.

        This method establishes a WebSocket connection to the OpenAI API using
        the specified model from the configuration. It sets up event handlers for
        WebSocket events, clears any previous completion events, and runs the WebSocket
        communication in a separate thread. The conversation will wait for the completion
        event to be set or a timeout of 60 seconds.

        Note:
            The connection utilizes threading to handle asynchronous communication
            with the OpenAI API.
        """
        uri = (
            f"wss://api.openai.com/v1/realtime?model={self.__config['interview_model']}"
        )
        header = [
            f"Authorization: Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta: realtime=v1",
        ]
        self.__done_event = asyncio.Event()

        def run_ws():
            self.__ws = websocket.WebSocketApp(
                uri,
                header=header,
                on_open=self.__on_open,
                on_message=self.__on_message_wrapper,
                on_error=self.__on_error,
                on_close=self.__on_close,
                # on_reconnect=self.__on_reconnect,
                # on_cont_message=self.__on_cont_message,
            )
            self.__ws.run_forever()

        threading.Thread(target=run_ws, daemon=True).start()
        await self.__done_event.wait()

    async def process_text_queue(self):
        """
        Processes the text queue asynchronously.

        This method runs in an infinite loop, pulling messages from the
        `text_queue` and sending them to the frontend WebSocket. If the frontend
        WebSocket is closed, the message is dropped and a warning is logged.

        The method will exit if the task is cancelled or if an unexpected error
        occurs. The error will be logged and the task will be exited.

        Note:
            This method is intended to run in a separate task.
        """
        while True:
            try:
                message = await self.text_queue.get()
                if self.fe_websocket.client_state == WebSocketState.CONNECTED:
                    await self.fe_websocket.send_text(message)

                else:
                    logger.warning(
                        "Frontend WebSocket is closed. Dropping message: %s",
                        message,
                    )
                self.text_queue.task_done()
            except asyncio.CancelledError:
                break  # Handle clean shutdown
            except Exception as e:
                logger.error("Error sending message from queue: %s", e)

    async def process_audio_queue(self):
        """
        Processes the audio queue asynchronously.

        This method continuously retrieves audio data from the `audio_queue` and sends it
        to the frontend WebSocket if the connection is active. If the connection is closed,
        the audio data is dropped and a warning is logged.

        The method will exit gracefully if the task is cancelled or log any unexpected
        errors that occur during the process.

        Note:
            This method is intended to run in a separate task.
        """

        while True:
            try:
                audio_data = await self.audio_queue.get()
                if self.fe_websocket.client_state == WebSocketState.CONNECTED:
                    await self.fe_websocket.send_bytes(audio_data)
                else:
                    logger.warning("Frontend WebSocket closed, dropping audio data")
                self.audio_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error sending audio data: %s", e)

    def __pcm16_to_wav_bytes(self, audio_data: bytes) -> bytes:
        """
        Saves the given audio data (in 16-bit PCM format) to a .wav file.

        Args:
            audio_data (bytes): The audio data in 16-bit PCM format.

        Returns:
            bytes: The audio data read back from the .wav file.
        """
        temp_file_path = os.path.join(os.getcwd(), "agent_response.wav")
        sample_rate = 24000
        # pylint: disable=no-member
        with wave.open(temp_file_path, "wb") as wf:
            wf.setnchannels(1)  # mono
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        # logger.debug("Audio saved to %s", temp_file_path)

        with open(temp_file_path, "rb") as temp_audio_file:
            agent_speech = temp_audio_file.read()
        # with io.BytesIO() as wav_buffer:
        #     with wave.open(wav_buffer, "wb") as wf:  # type: wave.Wave_write
        #         wf.setnchannels(1)  # mono
        #         wf.setsampwidth(2)  # 16-bit PCM
        #         wf.setframerate(sample_rate)
        #         wf.writeframes(audio_data)
        #     wav_buffer.seek(0)  # Move to the beginning of the BytesIO buffer
        #     agent_speech = wav_buffer.read()
        # logger.debug("Audio converted to WAV format with sample rate %d", sample_rate)
        return agent_speech

    def process_input_audio(self, user_audio: bytes) -> tuple:
        """
        Send a message to the WebSocket server using the "conversation.item.create"
        event. The message contains an "input_audio" element with the given
        user_audio.

        Args:
            user_audio (bytes|None): The audio data to be sent.

        Returns:
            tuple: A tuple containing the response from the server and any
                additional information that may have been sent.

        Raises:
            RuntimeError: If the WebSocket connection is closed.
        """
        if not user_audio:
            return  # Ignore empty audio packets
        # Convert WebM to PCM16 using pydub
        audio = AudioSegment.from_file(io.BytesIO(user_audio), format="webm")
        audio = audio.set_frame_rate(24000).set_channels(1).set_sample_width(2)  # PCM16

        # Save as PCM16 bytes
        pcm_audio = io.BytesIO()
        audio.export(pcm_audio, format="raw")
        pcm_audio_bytes = pcm_audio.getvalue()
        if self.__ws.sock and self.__ws.sock.connected:
            audio_base64 = base64.b64encode(pcm_audio_bytes).decode("utf-8")
            audio_event = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64,
            }

            # if self.__last_available_item_id is not None:
            #     conversation_event["previous_item_id"] = self.__last_available_item_id
            self.__ws.send(json.dumps(audio_event))
            logger.debug("Sent PCM16-encoded audio buffer append event.")
        else:
            logger.error("GPT webSocket connection is closed. Cannot send message.")
            raise RuntimeError("WebSocket connection is closed.")
        # self.__done_event.wait(timeout=60)
        self.__done_event.clear()
