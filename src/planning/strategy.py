"""Target selection for collecting all balls with minimal replanning overhead.

The planner keeps one active target at a time so the robot does not bounce
between balls while it is driving. After a pickup is confirmed, it re-evaluates
the remaining balls and picks the next best target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional

from src.vision.ball_detector import BallPosition


@dataclass(frozen=True)
class CompletedTarget:
    color: str
    x_cm: float
    y_cm: float


class PickupPlanner:
    """Stateful target selector for collecting balls in a greedy shortest-path order."""

    def __init__(
        self,
        field_map,
        pickup_match_radius_cm: float = 6.0,
        release_after_missing_frames: int = 3,
    ):
        self.field_map = field_map
        self.pickup_match_radius_cm = pickup_match_radius_cm
        self.release_after_missing_frames = release_after_missing_frames

        self.active_target: Optional[BallPosition] = None
        self._missing_frames = 0
        self._completed_targets: list[CompletedTarget] = []

    def _ball_to_cm(self, ball: BallPosition) -> tuple[float, float]:
        if self.field_map is None:
            return float(ball.x), float(ball.y)
        return self.field_map.pixel_to_cm(ball.x, ball.y)

    def _distance_cm(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _is_completed(self, ball: BallPosition) -> bool:
        ball_x, ball_y = self._ball_to_cm(ball)
        for completed in self._completed_targets:
            if completed.color != ball.color:
                continue
            if self._distance_cm((completed.x_cm, completed.y_cm), (ball_x, ball_y)) <= self.pickup_match_radius_cm:
                return True
        return False

    def _match_active_target(self, balls: Iterable[BallPosition]) -> Optional[BallPosition]:
        if self.active_target is None:
            return None

        active_x, active_y = self._ball_to_cm(self.active_target)
        for ball in balls:
            if ball.color != self.active_target.color:
                continue
            ball_x, ball_y = self._ball_to_cm(ball)
            if self._distance_cm((active_x, active_y), (ball_x, ball_y)) <= self.pickup_match_radius_cm:
                return ball
        return None

    def choose_target(self, balls: Iterable[BallPosition], robot_pos_cm: tuple[float, float]) -> Optional[BallPosition]:
        """Choose the next ball to collect.

        Orange is prioritized when present. Otherwise the nearest uncollected
        ball is selected. The current target is kept until it is lost for a few
        frames or confirmed as collected.
        """

        candidates = [ball for ball in balls if not self._is_completed(ball)]
        if not candidates:
            self.active_target = None
            self._missing_frames = 0
            return None

        if self.active_target is not None:
            matched = self._match_active_target(candidates)
            if matched is not None:
                self.active_target = matched
                self._missing_frames = 0
                return matched

            self._missing_frames += 1
            if self._missing_frames < self.release_after_missing_frames:
                return self.active_target

            self.active_target = None
            self._missing_frames = 0

        orange_candidates = [ball for ball in candidates if ball.color == "orange"]
        pool = orange_candidates if orange_candidates else candidates

        chosen = min(
            pool,
            key=lambda ball: (
                self._distance_cm(robot_pos_cm, self._ball_to_cm(ball)),
                -ball.area,
            ),
        )
        self.active_target = chosen
        self._missing_frames = 0
        return chosen

    def target_is_visible(self, balls: Iterable[BallPosition]) -> bool:
        """Return True when the active target is still visible in the latest frame."""

        return self._match_active_target(balls) is not None

    def confirm_pickup(self) -> Optional[BallPosition]:
        """Mark the active target as collected and clear it from the route."""

        if self.active_target is None:
            return None

        x_cm, y_cm = self._ball_to_cm(self.active_target)
        picked = self.active_target
        self._completed_targets.append(
            CompletedTarget(color=picked.color, x_cm=x_cm, y_cm=y_cm)
        )
        self.active_target = None
        self._missing_frames = 0
        return picked
