import pytest


@pytest.fixture
def mongodb_conn(mocker):
    """Create a mock MongoDB database connection."""
    # Mock MongoDB database connection
    mock_db = mocker.MagicMock()
    mock_db.database = mocker.MagicMock()
    mock_db.list_collection_names = mocker.MagicMock(return_value=["test_collection"])

    # Mock collection
    mock_collection = mocker.MagicMock()
    mock_collection.find_one = mocker.MagicMock(return_value={"test": "value"})
    mock_collection.insert_one = mocker.MagicMock(
        return_value=mocker.MagicMock(inserted_id="507f1f77bcf86cd799439011")
    )
    mock_collection.find = mocker.MagicMock(return_value=[{"test": "value"}])
    mock_collection.delete_many = mocker.MagicMock(
        return_value=mocker.MagicMock(deleted_count=1)
    )
    mock_collection.update_one = mocker.MagicMock(
        return_value=mocker.MagicMock(modified_count=1)
    )

    # Mock database to return collection when accessed with []
    mock_db.__getitem__ = mocker.MagicMock(return_value=mock_collection)

    return mock_db
