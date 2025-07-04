"""
Formatter module that converts JSON interview analysis data into styled HTML reports.

This module provides functionality to transform structured JSON data containing
interview analysis results into a well-formatted HTML report. It includes features
for:
- Score visualization using progress bars
- Gauge charts for overall scores
- Structured section formatting
- Q&A similarity analysis table generation
- Facial expression analysis visualization
- Overall result summary formatting

The main class, Formatter, processes the JSON input and renders it using a Jinja2
template to produce a professional-looking HTML report that can be viewed in a web
browser or converted to PDF.
"""

import math
import os
from typing import Any, Dict, List

from jinja2 import Template

from user_management import Candidate


class Formatter:
    """Processes Markdown string into styled HTML using a template."""

    def __init__(self, input_json: Dict[str, Any], candidate: Candidate):
        self.input_json = input_json
        self.candidate = candidate

    def __generate_qa_table_html(self, table_data: List[List[str]]):
        rows = []
        for row in table_data:
            question_num, question, candidate_response, ideal_response, score = row
            rows.append(
                f"""
                <tr>
                    <td>{question_num}</td>
                    <td>{question}</td>
                    <td>{candidate_response}</td>
                    <td>{ideal_response}</td>
                    <td>{score}</td>
                </tr>
            """
            )
        return "\n".join(rows)

    def __gauge_svg(self, percentage: float) -> str:
        """
        Draws an enlarged multi-colored top half-circle gauge from left (0%) to right (100%).
        The gauge is segmented into five arcs and segment labels centered within the arcs
        (displayed in white). The needle pointer is rendered as a sharp triangular pointer,
        and the pivot circle is larger.
        """
        svg_width = 300
        svg_height = 300

        # New center and radius (approximately doubled from previous dimensions)
        cx, cy = 150, 150  # 240 / 480 * 300 = 150
        r = 100  # 160 / 480 * 300 = 100
        stroke_w = 60  # increased thickness of each colored arc 100 / 480 * 300 = 62.5, rounded to 60

        segments: List[Dict[str, Any]] = [
            {"start": 180, "end": 144, "color": "#ef5350", "label": "Poor"},
            {"start": 142, "end": 108, "color": "#ff9800", "label": "Fair"},
            {"start": 106, "end": 72, "color": "#fbc02d", "label": "Good"},
            {"start": 70, "end": 36, "color": "#8bc34a", "label": "Great"},
            {"start": 34, "end": 0, "color": "#66bb6a", "label": "Excellent"},
        ]

        # Numeric boundaries: (value, angle)
        # boundaries = [
        #     (0, 180),
        #     (20, 144),
        #     (40, 108),
        #     (60, 72),
        #     (80, 36),
        #     (100, 0),
        # ]

        def polar_to_cartesian(cx, cy, radius, angle_deg):
            """Convert polar coordinates to Cartesian. In SVG, Y increases downward."""
            rad = math.radians(angle_deg)
            x = cx + radius * math.cos(rad)
            y = cy - radius * math.sin(rad)
            return x, y

        def arc_path(cx, cy, radius, angle_start, angle_end):
            """Return the SVG path for an arc from angle_start to angle_end (in degrees)."""
            start_x, start_y = polar_to_cartesian(cx, cy, radius, angle_start)
            end_x, end_y = polar_to_cartesian(cx, cy, radius, angle_end)
            return f"M {start_x:.2f},{start_y:.2f} A {radius},{radius} 0 0 1 {end_x:.2f},{end_y:.2f}"

        svg_parts = [
            f'<svg viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}"class="gauge-svg">'
        ]

        # Draw each colored arc segment (with butt linecaps to preserve gaps).
        for seg in segments:
            d = arc_path(cx, cy, r, seg["start"], seg["end"])
            svg_parts.append(
                f'<path d="{d}" fill="none" stroke="{seg["color"]}" '
                f'stroke-width="{stroke_w}" stroke-linecap="butt" />'
            )

        # Add circles at the endpoints to simulate rounded ends.
        first_seg = segments[0]
        start_point = polar_to_cartesian(cx, cy, r, first_seg["start"])
        svg_parts.append(
            f'<circle cx="{start_point[0]:.2f}" cy="{start_point[1]:.2f}" r="{stroke_w/2}" fill="{first_seg["color"]}" />'
        )
        last_seg = segments[-1]
        end_point = polar_to_cartesian(cx, cy, r, last_seg["end"])
        svg_parts.append(
            f'<circle cx="{end_point[0]:.2f}" cy="{end_point[1]:.2f}" r="{stroke_w/2}" fill="{last_seg["color"]}" />'
        )

        # Draw numeric boundary labels (0,20,40,60,80,100) inside the gauge.
        # Moved inward using radius: r - stroke_w/2 - 5.
        # offset_inward = 15
        # for val, angle in boundaries:
        #     x_lbl, y_lbl = polar_to_cartesian(
        #         cx, cy, r - stroke_w / 2 - offset_inward, angle
        #     )
        #     svg_parts.append(
        #         f'<text x="{x_lbl:.2f}" y="{y_lbl:.2f}" text-anchor="middle" dominant-baseline="middle" '
        #         f'font-size="14" fill="#333" font-weight="bold">{val}</text>'
        #     )

        # Place segment labels inside each colored arc.
        # Using radius: r so that the text appears at the center of the stroke.
        for seg in segments:
            mid_angle = (seg["start"] + seg["end"]) / 2
            x_mid, y_mid = polar_to_cartesian(cx, cy, r, mid_angle)
            svg_parts.append(
                f'<text x="{x_mid:.2f}" y="{y_mid:.2f}" text-anchor="middle" dominant-baseline="middle" '
                f'font-size="12" fill="#fff" font-weight="bold">{seg["label"]}</text>'
            )

        # Compute the needle angle: 180° at 0% → 0° at 100%.
        needle_angle = 180.0 - (percentage * 180.0 / 100.0)
        needle_len = r - 10  # Needle length (proportionate to gauge size)
        x2, y2 = polar_to_cartesian(cx, cy, needle_len, needle_angle)

        # Draw a sharp needle pointer as a triangle.
        pointer_width = 12
        perp_angle = needle_angle + 90  # Perpendicular to the needle
        base_offset = pointer_width / 2
        base_left = polar_to_cartesian(cx, cy, base_offset, perp_angle)
        base_right = polar_to_cartesian(cx, cy, base_offset, perp_angle - 180)
        svg_parts.append(
            f'<polygon points="{x2:.2f},{y2:.2f} {base_left[0]:.2f},{base_left[1]:.2f} {base_right[0]:.2f},{base_right[1]:.2f}" '
            f'fill="#333" />'
        )

        # Draw the pivot circle (needle round) with increased radius.
        pivot_radius = 25
        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{pivot_radius}" fill="#333" />'
        )
        # Display the numeric percentage inside the pivot circle.
        svg_parts.append(
            f'<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="20" fill="#fff" font-weight="bold">{percentage:.0f}</text>'
        )

        svg_parts.append("</svg>")
        return "".join(svg_parts)

    def __call__(self) -> str:
        with open(
            os.path.join(os.path.dirname(__file__), "template.html"),
            "r",
            encoding="utf-8",
        ) as f:
            html_template = Template(f.read())
        return html_template.render(
            candidate_name=self.candidate.user_profile.name,
            candidate_id=self.candidate.user_id,
            clarity_score=self.input_json["Speech Analysis"]["Clarity"]["score"] * 10,
            clarity_text=self.input_json["Speech Analysis"]["Clarity"]["reasoning"],
            fluency_score=self.input_json["Speech Analysis"]["Fluency"]["score"] * 10,
            fluency_text=self.input_json["Speech Analysis"]["Fluency"]["reasoning"],
            pronunciation_score=self.input_json["Speech Analysis"]["Pronunciation"][
                "score"
            ]
            * 10,
            pronunciation_text=self.input_json["Speech Analysis"]["Pronunciation"][
                "reasoning"
            ],
            technical_proficiency_score=self.input_json["Competency Analysis"][
                "Technical Proficiency"
            ]["score"]
            * 10,
            technical_proficiency_text=self.input_json["Competency Analysis"][
                "Technical Proficiency"
            ]["reasoning"],
            contextual_application_score=self.input_json["Competency Analysis"][
                "Contextual Application"
            ]["score"]
            * 10,
            contextual_application_text=self.input_json["Competency Analysis"][
                "Contextual Application"
            ]["reasoning"],
            articulation_score=self.input_json["Grammar & Diction"]["Articulation"][
                "score"
            ]
            * 10,
            articulation_text=self.input_json["Grammar & Diction"]["Articulation"][
                "reasoning"
            ],
            conciseness_score=self.input_json["Grammar & Diction"][
                "Clarity & Conciseness"
            ]["score"]
            * 10,
            conciseness_text=self.input_json["Grammar & Diction"][
                "Clarity & Conciseness"
            ]["reasoning"],
            grammar_score=self.input_json["Grammar & Diction"]["Grammar & Vocabulary"][
                "score"
            ]
            * 10,
            grammar_text=self.input_json["Grammar & Diction"]["Grammar & Vocabulary"][
                "reasoning"
            ],
            facial_expression_score=self.input_json["Facial Expression Analysis"][
                "score"
            ]
            * 10,
            facial_expression_overall_impression=self.input_json[
                "Facial Expression Analysis"
            ]["Overall Impression"],
            facial_expression_specific_observations=self.input_json[
                "Facial Expression Analysis"
            ]["Specific Observations"],
            facial_expression_final_assessment=self.input_json[
                "Facial Expression Analysis"
            ]["Final Assessment"],
            overall_summary=self.input_json["Overall Result"]["Summary"],
            recommendations=self.input_json["Overall Result"]["Recommendations"],
            gauge_svg=self.__gauge_svg(
                self.input_json["Overall Result"]["Overall Score"] * 10
            ),
            qa_table_rows=self.__generate_qa_table_html(
                self.input_json["Q&A Similarity Analysis"]["table"]
            ),
        )
