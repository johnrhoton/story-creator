import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from database.migrations import run_migrations
from database.observability import get_app_events, log_app_event
from database.schema import create_tables
from services.observability_service import (
    build_event_dict,
    get_metrics_counters,
    log_event,
    operation_events,
    timed_operation,
)


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


class ObservabilityTests(unittest.TestCase):
    def test_app_event_round_trips_all_core_fields(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            log_app_event(
                "story_generation_completed",
                status="completed",
                duration_ms=42.5,
                story_id=10,
                chapter_id=20,
                template_id=30,
                character_id=40,
                provider="Groq",
                model="test-model",
                token_estimate=123,
                metadata_json='{"source": "test"}',
            )

            events = get_app_events()

            self.assertEqual(len(events), 1)
            event = build_event_dict(events[0])
            self.assertEqual(event["event_type"], "story_generation_completed")
            self.assertEqual(event["status"], "completed")
            self.assertEqual(event["duration_ms"], 42.5)
            self.assertEqual(event["story_id"], 10)
            self.assertEqual(event["chapter_id"], 20)
            self.assertEqual(event["template_id"], 30)
            self.assertEqual(event["character_id"], 40)
            self.assertEqual(event["provider"], "Groq")
            self.assertEqual(event["model"], "test-model")
            self.assertEqual(event["token_estimate"], 123)
            self.assertEqual(event["metadata"], {"source": "test"})

    def test_operation_events_records_failure_duration_and_error(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            with self.assertRaisesRegex(ValueError, "boom"):
                with operation_events(
                    "chapter_generation_started",
                    "chapter_generation_completed",
                    "chapter_generation_failed",
                    story_id=1,
                    chapter_id=2,
                ):
                    raise ValueError("boom")

            events = [
                build_event_dict(row)
                for row in get_app_events()
            ]

            self.assertEqual(
                [event["event_type"] for event in events],
                ["chapter_generation_failed", "chapter_generation_started"]
            )
            self.assertEqual(events[0]["status"], "failed")
            self.assertIsNotNone(events[0]["duration_ms"])
            self.assertEqual(events[0]["error_type"], "ValueError")
            self.assertEqual(events[0]["error_message"], "boom")

    def test_log_event_records_python_log_and_metric_counter(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            with self.assertLogs(
                "services.observability_service",
                level="INFO",
            ) as logs:
                log_event(
                    "unit_test_event",
                    status="completed",
                    metadata={"source": "test"},
                    story_id=7,
                )

            self.assertIn(
                "event=unit_test_event status=completed story_id=7",
                logs.output[0],
            )
            self.assertGreaterEqual(
                get_metrics_counters().get(
                    "events.unit_test_event.completed",
                    0,
                ),
                1,
            )

    def test_timed_operation_records_duration_and_operation_metadata(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            with timed_operation(
                "database_save",
                completed_event_type="database_save_completed",
                metadata={"table": "stories"},
                story_id=3,
            ):
                pass

            event = build_event_dict(get_app_events()[0])

            self.assertEqual(event["event_type"], "database_save_completed")
            self.assertEqual(event["status"], "completed")
            self.assertIsNotNone(event["duration_ms"])
            self.assertEqual(event["story_id"], 3)
            self.assertEqual(
                event["metadata"],
                {"table": "stories", "operation": "database_save"},
            )


if __name__ == "__main__":
    unittest.main()
