import pytest
from datetime import datetime
from app.utils import chunk_locations, get_trips_chunks, check_schema_equality, translate_method_to_action


class TestChunkLocations:
    """Casos de teste para função chunk_locations."""
    
    def test_chunk_locations_normal_case(self):
        """Testa comportamento normal de chunking."""
        locations = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = chunk_locations(locations, 3)
        expected = [[1, 2, 3], [3, 4, 5], [5, 6, 7], [7, 8, 9], [9, 10]]
        assert result == expected
    
    def test_chunk_locations_n_equals_length(self):
        """Testa quando N é igual ao comprimento das localizações."""
        locations = [1, 2, 3, 4, 5]
        result = chunk_locations(locations, 5)
        expected = [[1, 2, 3, 4, 5]]
        assert result == expected
    
    def test_chunk_locations_n_greater_than_length(self):
        """Testa quando N é maior que o comprimento das localizações."""
        locations = [1, 2, 3]
        result = chunk_locations(locations, 5)
        expected = [[1, 2, 3]]
        assert result == expected
    
    def test_chunk_locations_n_equals_one(self):
        """Testa quando N é igual a 1."""
        locations = [1, 2, 3, 4]
        result = chunk_locations(locations, 1)
        expected = [[1, 2, 3, 4]]
        assert result == expected
    
    def test_chunk_locations_empty_list(self):
        """Testa com lista vazia de localizações."""
        locations = []
        result = chunk_locations(locations, 3)
        expected = [[]]
        assert result == expected
    
    def test_chunk_locations_single_element(self):
        """Testa com um único elemento."""
        locations = [1]
        result = chunk_locations(locations, 2)
        expected = [[1]]
        assert result == expected


class TestGetTripsChunks:
    """Casos de teste para função get_trips_chunks."""
    
    def test_get_trips_chunks_normal_case(self):
        """Testa comportamento normal de chunking de viagens."""
        locations = [
            {"datahora": datetime(2023, 1, 1, 10, 0, 0), "id": 1},
            {"datahora": datetime(2023, 1, 1, 10, 30, 0), "id": 2},
            {"datahora": datetime(2023, 1, 1, 12, 0, 0), "id": 3},  # 1.5 hours later
            {"datahora": datetime(2023, 1, 1, 12, 15, 0), "id": 4},
        ]
        max_time_interval = 3600  # 1 hour
        
        result = get_trips_chunks(locations, max_time_interval)
        
        # Should create 2 chunks due to the 1.5 hour gap
        assert len(result) == 2
        assert len(result[0]) == 2  # First chunk: items 1, 2
        assert len(result[1]) == 2  # Second chunk: items 3, 4
        
        # Check that seconds_to_next_point is set correctly
        assert result[0][0]["seconds_to_next_point"] == 1800  # 30 minutes
        assert result[0][1]["seconds_to_next_point"] is None  # Last in chunk
        assert result[1][0]["seconds_to_next_point"] == 900   # 15 minutes
        assert result[1][1]["seconds_to_next_point"] is None  # Last in chunk
    
    def test_get_trips_chunks_single_trip(self):
        """Testa com localizações que formam uma única viagem."""
        locations = [
            {"datahora": datetime(2023, 1, 1, 10, 0, 0), "id": 1},
            {"datahora": datetime(2023, 1, 1, 10, 15, 0), "id": 2},
            {"datahora": datetime(2023, 1, 1, 10, 30, 0), "id": 3},
        ]
        max_time_interval = 3600  # 1 hour
        
        result = get_trips_chunks(locations, max_time_interval)
        
        assert len(result) == 1
        assert len(result[0]) == 3
        assert result[0][2]["seconds_to_next_point"] is None
    
    def test_get_trips_chunks_empty_locations(self):
        """Testa com lista vazia de localizações."""
        locations = []
        max_time_interval = 3600
        
        result = get_trips_chunks(locations, max_time_interval)
        
        assert result == []
    
    def test_get_trips_chunks_single_location(self):
        """Testa com uma única localização."""
        locations = [
            {"datahora": datetime(2023, 1, 1, 10, 0, 0), "id": 1}
        ]
        max_time_interval = 3600
        
        result = get_trips_chunks(locations, max_time_interval)
        
        assert len(result) == 1
        assert len(result[0]) == 1
        assert result[0][0]["seconds_to_next_point"] is None


class TestCheckSchemaEquality:
    """Casos de teste para função check_schema_equality."""
    
    def test_simple_dict_equality(self):
        """Testa igualdade de dicionário simples."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"a": 1, "b": 2}
        assert check_schema_equality(dict1, dict2) is True
    
    def test_simple_dict_inequality(self):
        """Testa desigualdade de dicionário simples."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"a": 1, "b": 3}
        assert check_schema_equality(dict1, dict2) is False
    
    def test_nested_dict_equality(self):
        """Testa igualdade de dicionário aninhado."""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"x": 1, "y": 2}, "b": 3}
        assert check_schema_equality(dict1, dict2) is True
    
    def test_nested_dict_inequality(self):
        """Testa desigualdade de dicionário aninhado."""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"x": 1, "y": 3}, "b": 3}
        assert check_schema_equality(dict1, dict2) is False
    
    def test_list_equality(self):
        """Testa igualdade de dicionário com lista."""
        dict1 = {"a": [1, 2, 3], "b": "test"}
        dict2 = {"a": [1, 2, 3], "b": "test"}
        assert check_schema_equality(dict1, dict2) is True
    
    def test_list_inequality(self):
        """Testa desigualdade de dicionário com lista."""
        dict1 = {"a": [1, 2, 3], "b": "test"}
        dict2 = {"a": [1, 2, 4], "b": "test"}
        assert check_schema_equality(dict1, dict2) is False
    
    def test_list_with_nested_dicts(self):
        """Testa lista contendo dicionários aninhados."""
        dict1 = {"items": [{"name": "test1", "value": 1}, {"name": "test2", "value": 2}]}
        dict2 = {"items": [{"name": "test1", "value": 1}, {"name": "test2", "value": 2}]}
        assert check_schema_equality(dict1, dict2) is True
    
    def test_list_with_nested_dicts_inequality(self):
        """Testa lista contendo dicionários aninhados com desigualdade."""
        dict1 = {"items": [{"name": "test1", "value": 1}, {"name": "test2", "value": 2}]}
        dict2 = {"items": [{"name": "test1", "value": 1}, {"name": "test2", "value": 3}]}
        assert check_schema_equality(dict1, dict2) is False


class TestTranslateMethodToAction:
    """Casos de teste para função translate_method_to_action."""
    
    def test_get_method(self):
        """Testa tradução do método GET."""
        assert translate_method_to_action("GET") == "read"
        assert translate_method_to_action("get") == "read"
    
    def test_post_method(self):
        """Testa tradução do método POST."""
        assert translate_method_to_action("POST") == "create"
        assert translate_method_to_action("post") == "create"
    
    def test_put_method(self):
        """Testa tradução do método PUT."""
        assert translate_method_to_action("PUT") == "update"
        assert translate_method_to_action("put") == "update"
    
    def test_delete_method(self):
        """Testa tradução do método DELETE."""
        assert translate_method_to_action("DELETE") == "delete"
        assert translate_method_to_action("delete") == "delete"
    
    def test_unknown_method(self):
        """Testa tradução de método desconhecido."""
        assert translate_method_to_action("PATCH") == "read"  # Default fallback
        assert translate_method_to_action("OPTIONS") == "read"
        assert translate_method_to_action("unknown") == "read"
    
    def test_mixed_case_methods(self):
        """Testa nomes de métodos com casos mistos."""
        assert translate_method_to_action("Get") == "read"
        assert translate_method_to_action("Post") == "create"
        assert translate_method_to_action("PUT") == "update"