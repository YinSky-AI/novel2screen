# Unit tests for agent base class
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
from agents.base import AgentBase, AgentError

class MockAgent(AgentBase):
    def __init__(self):
        super().__init__(name='MockAgent')
        self.call_count = 0

    def run(self, input_data):
        self.call_count += 1
        return {'result': 'ok', 'call': self.call_count}

    def validate(self, output):
        return output.get('result') == 'ok'

def test_agent_run():
    agent = MockAgent()
    result = agent.run({'test': True})
    assert result['result'] == 'ok'
    print("test_agent_run: PASS")

def test_agent_validate():
    agent = MockAgent()
    assert agent.validate({'result': 'ok'})
    assert not agent.validate({'result': 'bad'})
    print("test_agent_validate: PASS")

def test_agent_retry():
    agent = MockAgent()
    result = agent.retry({'test': True})
    assert result['result'] == 'ok'
    assert agent.get_attempt_count() == 1
    print("test_agent_retry: PASS")

def test_agent_name():
    agent = MockAgent()
    assert agent.name == 'MockAgent'
    print("test_agent_name: PASS")

if __name__ == '__main__':
    test_agent_run()
    test_agent_validate()
    test_agent_retry()
    test_agent_name()
    print("All agent tests passed!")
