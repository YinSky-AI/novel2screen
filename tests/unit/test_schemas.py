# Unit tests for schema validation
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
import json, yaml
from schemas.models import Screenplay, Character, Episode, Scene, Beat
from schemas.validator import validate_screenplay_yaml, screenplay_to_yaml

def test_valid_screenplay():
    sp = Screenplay(
        title='Test', logline='Test logline', genre='Drama',
        theme='Testing',
        characters=[
            Character(id='char_001', name='Hero', role='protagonist', goal='Save world', arc='Growth')
        ],
        episodes=[
            Episode(
                id='ep_001', title='Pilot', summary='First episode',
                scenes=[
                    Scene(
                        scene_id='sc_001', location='City', time='Night',
                        beats=[Beat(type='action', content='Hero arrives')],
                        transition='cut', duration_estimate='60s'
                    )
                ]
            )
        ]
    )
    yaml_str = screenplay_to_yaml(sp)
    valid, errors = validate_screenplay_yaml(yaml_str)
    assert valid, f'Expected valid but got errors: {errors}'
    print("test_valid_screenplay: PASS")

def test_invalid_screenplay():
    invalid_yaml = "title: Only Title"
    valid, errors = validate_screenplay_yaml(invalid_yaml)
    assert not valid, 'Expected invalid'
    print("test_invalid_screenplay: PASS")

def test_character_roles():
    import traceback
    try:
        c = Character(id='char_001', name='Test', role='protagonist', goal='G1', arc='A1')
        assert c.role == 'protagonist'
    except Exception as e:
        assert False, f'Unexpected: {e}'
    print("test_character_roles: PASS")

def test_beat_validation():
    try:
        b = Beat(type='dialogue', character_id='char_001', content='Hello!', emotion='happy')
        assert b.type == 'dialogue'
    except Exception as e:
        assert False, f'Unexpected: {e}'
    print("test_beat_validation: PASS")

if __name__ == '__main__':
    test_valid_screenplay()
    test_invalid_screenplay()
    test_character_roles()
    test_beat_validation()
    print("All schema tests passed!")
