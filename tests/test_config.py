"""
Tests for configuration management.
"""

import pytest
import tempfile
from pathlib import Path

from config import Config, load_config


def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config_data = {
        "input_excel": "test.xlsx",
        "email": "test@example.com",
        "strings": ["machine learning", "neural network"]
    }
    config = Config(**config_data)
    assert config.email == "test@example.com"
    assert len(config.strings) == 2
    
    # Invalid email
    with pytest.raises(ValueError, match="Email must contain @ symbol"):
        Config(input_excel="test.xlsx", email="invalid-email", strings=["test"])
    
    # Empty strings
    with pytest.raises(ValueError, match="At least one search string must be provided"):
        Config(input_excel="test.xlsx", email="test@example.com", strings=[])


def test_config_from_yaml():
    """Test loading configuration from YAML file."""
    yaml_content = """
input_excel: "doi_data.xlsx"
email: "researcher@university.edu"
strings:
  - "machine learning"
  - "artificial intelligence"
output_dir: "results"
batch_size: 10

logging:
  level: "DEBUG"
  file: "custom.log"

http:
  user_agent: "custom-agent/1.0"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        config = load_config(f.name)
        assert config.email == "researcher@university.edu"
        assert config.batch_size == 10
        assert config.logging.level == "DEBUG"
        assert config.http.user_agent == "custom-agent/1.0"
        
        # Clean up
        Path(f.name).unlink()