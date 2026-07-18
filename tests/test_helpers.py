import pytest

from mdfb.utils.helpers import get_chunk, split_list


def test_split_list():
    mock_posts = ["hello", "world", "!"]
    mock_split_by = 3
    result = split_list(mock_posts, mock_split_by)
    assert result == [["hello"], ["world"], ["!"]]


def test_split_list_zero():
    mock_posts = ["hello", "world", "!"]
    mock_split_by = 0
    with pytest.raises(ValueError):
        split_list(mock_posts, mock_split_by)


def test_get_chunk():
    mock_posts = ["hello", "world", "!"]
    mock_chunk_size = 2
    result = list(get_chunk(mock_posts, mock_chunk_size))
    assert result == [["hello", "world"], ["!"]]


def test_get_chunk_zero_chunk_size():
    mock_posts = ["hello", "world", "!"]
    mock_chunk_size = -2
    with pytest.raises(ValueError):
        list(get_chunk(mock_posts, mock_chunk_size))


def test_get_chunk_zero_posts():
    mock_posts = []
    mock_chunk_size = 1
    result = list(get_chunk(mock_posts, mock_chunk_size))
    assert result == []
