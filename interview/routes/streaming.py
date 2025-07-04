"""
routes.py

This module contains WebSocket endpoints for handling audio and video streaming
for the interview process. It includes functionalities for receiving and processing
audio and video data from candidates during interviews.

Endpoints:
- /audio: WebSocket endpoint for audio streaming.
- /video: WebSocket endpoint for video streaming.
"""

import asyncio
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from commons import FileName, RecordNotFoundException, logger
from interview.src.interview_manager import InterviewManager
from interview.src.open_ai_connector import OpenAIOrchestrator
from reporting import InterviewSummary
from user_management import get_current_user

router = APIRouter(tags=["interview"], prefix="/interview")
# Shared event to track audio WebSocket state
audio_websocket_events = {}


@router.websocket("/audio")
async def audio(fe_websocket: WebSocket):
    """
    Handles the WebSocket connection for audio interviews.

    This function accepts a WebSocket connection and manages the
    communication between the client and the server, sending and
    receiving audio data during the interview process.

    Args:
        fe_websocket (WebSocket): The WebSocket connection instance.
    """
    logger.debug("Starting Interview...")
    token = fe_websocket.query_params.get("token")

    if token is None:
        logger.error("Token is not provided. Closing connection...")
        await fe_websocket.close()
        return

    candidate_id = get_current_user(token)
    await fe_websocket.accept()
    audio_websocket_events[candidate_id] = asyncio.Event()
    try:
        interview_obj = InterviewManager(candidate_id)
        if not interview_obj.pre_requisites():
            await fe_websocket.send_text("Interview pre-requisites not found")
            await fe_websocket.close()
            return
        instructions = interview_obj.get_instructions()
        open_ai_orchestrator = OpenAIOrchestrator(instructions, fe_websocket)
        await open_ai_orchestrator.start_conversation()
        interview_obj.move_status_to_in_progress()

        while True:
            try:
                logger.debug("Receiving candidate's audio...")
                candidate_audio = await fe_websocket.receive_bytes()

                logger.debug("Received audio chunk, processing...")
                open_ai_orchestrator.process_input_audio(candidate_audio)
            except WebSocketDisconnect:
                logger.warning("WebSocket disconnected from candidate!")
                break
            except (
                KeyError,
                TypeError,
                ValueError,
                ConnectionResetError,
                RuntimeError,
            ) as e:
                logger.exception(
                    "Error occurred while processing candidate audio: %s", str(e)
                )
                break
    except (RecordNotFoundException, FileNotFoundError) as e:
        logger.exception("Error occurred in outer loop: %s", str(e))
        await fe_websocket.send_text(str(e))
    except (
        WebSocketDisconnect,
        ValueError,
        TypeError,
        KeyError,
        ConnectionResetError,
        RuntimeError,
    ) as e:
        logger.exception("Error occurred in outer loop: %s", str(e))
    if fe_websocket.client_state == WebSocketState.CONNECTED:
        await fe_websocket.close()
        logger.info("Audio WebSocket connection closed gracefully from backend !")
    interview_obj.generate_transcript(open_ai_orchestrator.transcript)
    interview_obj.stop()
    logger.info("Interview completed for candidate %s", candidate_id)
    audio_websocket_events[candidate_id].set()


@router.websocket("/video")
async def video_streaming(fe_websocket: WebSocket):
    """
    Handles video reception from the client for a given candidate.

    This endpoint accepts a WebSocket connection and stores the received video
    chunks in the correct location using an InterviewManager instance.

    Parameters:
    - candidate_id (int): The ID of the candidate for whom the video is being
      recorded.
    - fe_websocket (WebSocket): The WebSocket object to receive and send messages.

    Returns:
    - None
    """
    token = fe_websocket.query_params.get("token")

    if token is None:
        logger.error("Token is not provided. Closing connection...")
        await fe_websocket.close()
        return
    candidate_id = get_current_user(token)

    await fe_websocket.accept()

    interview_obj = InterviewManager(candidate_id)
    if not interview_obj.pre_requisites():
        await fe_websocket.send_text("Interview pre-requisites not found")
        await fe_websocket.close()
        return
    logger.info("Starting video reception for candidate %s", candidate_id)
    chunks = 0
    try:
        video_file_path = os.path.join(
            interview_obj.output_dir, f"{FileName.VIDEO.value}.webm"
        )
        with open(video_file_path, "wb") as video_fh:
            while True:
                try:
                    # logger.debug("Waiting to receive video chunk %s...", chunks)
                    message = await fe_websocket.receive()

                    if "text" in message and message["text"] == "TRANSFER_COMPLETE":
                        logger.info("Transfer completed from Frontend !")
                        break
                    if "bytes" in message:
                        candidate_video = message["bytes"]
                        if not candidate_video:
                            continue
                        video_fh.write(candidate_video)

                        logger.debug("Received and stored chunk %s", chunks)
                        chunks += 1
                    else:
                        continue
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected. Stopping video reception.")
                    break
                except RuntimeError as e:
                    logger.exception("RuntimeError while receiving message: %s", str(e))
                    break
                except Exception as e:
                    logger.exception("Error while receiving video: %s", str(e))
                    break
            video_fh.flush()
    except (OSError, IOError, PermissionError) as e:
        logger.exception("Error moving or saving the video file: %s", e)
    except Exception as e:
        logger.exception("Unexpected error during video reception: %s", str(e))
    if chunks > 0:
        logger.info("Video saved to: %s", video_file_path)
        logger.info(
            "Video reception completed for candidate %s. Total chunks: %s",
            candidate_id,
            chunks,
        )
        interview_obj.remux_video()
        if candidate_id in audio_websocket_events:
            logger.debug(
                "Waiting for Audio WebSocket event for candidate %s", candidate_id
            )
            await audio_websocket_events[candidate_id].wait()
            audio_websocket_events.pop(candidate_id, None)
            logger.info(
                "Audio WebSocket event received in video stream for candidate %s",
                candidate_id,
            )
            InterviewSummary(candidate_id, interview_obj.qa_dir)()
        else:
            logger.warning(
                "Audio WebSocket event not found for candidate %s", candidate_id
            )
    else:
        logger.warning("No video chunks received.")
