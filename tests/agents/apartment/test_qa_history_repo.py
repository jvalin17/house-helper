"""Q&A history repository — tests for saving and retrieving Q&A pairs."""

import sqlite3
import pytest
from shared.db import migrate
from agents.apartment.repositories.qa_history_repo import QaHistoryRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    connection.execute("INSERT INTO apartment_listings (id, title, price) VALUES (1, 'Alexan Braker Pointe', 1445)")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def qa_repo(database_connection):
    return QaHistoryRepository(database_connection)


class TestQaHistory:
    def test_save_and_retrieve_qa(self, qa_repo):
        qa_repo.save_qa(1, "Is this good for a dog owner?", "The listing mentions pet-friendly amenities...")
        history = qa_repo.get_history(1)
        assert len(history) == 1
        assert history[0]["question"] == "Is this good for a dog owner?"
        assert "pet-friendly" in history[0]["answer"]

    def test_history_returns_chronological_order(self, qa_repo):
        qa_repo.save_qa(1, "First question?", "First answer.")
        qa_repo.save_qa(1, "Second question?", "Second answer.")
        qa_repo.save_qa(1, "Third question?", "Third answer.")
        history = qa_repo.get_history(1)
        assert len(history) == 3
        assert history[0]["question"] == "First question?"
        assert history[2]["question"] == "Third question?"

    def test_history_empty_initially(self, qa_repo):
        history = qa_repo.get_history(1)
        assert history == []

    def test_history_respects_limit(self, qa_repo):
        for question_number in range(10):
            qa_repo.save_qa(1, f"Question {question_number}?", f"Answer {question_number}.")
        history = qa_repo.get_history(1, limit=3)
        assert len(history) == 3
        # Should be the 3 most recent in chronological order
        assert history[0]["question"] == "Question 7?"
        assert history[2]["question"] == "Question 9?"

    def test_history_scoped_to_listing(self, qa_repo, database_connection):
        database_connection.execute("INSERT INTO apartment_listings (id, title, price) VALUES (2, 'Camden', 1100)")
        database_connection.commit()
        qa_repo.save_qa(1, "About Alexan?", "Alexan answer.")
        qa_repo.save_qa(2, "About Camden?", "Camden answer.")
        history_alexan = qa_repo.get_history(1)
        history_camden = qa_repo.get_history(2)
        assert len(history_alexan) == 1
        assert len(history_camden) == 1
        assert history_alexan[0]["question"] == "About Alexan?"
        assert history_camden[0]["question"] == "About Camden?"
