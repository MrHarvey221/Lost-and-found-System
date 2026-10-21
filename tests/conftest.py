from contextlib import ExitStack
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from config import Settings
from main import create_app
from security import hash_password
import models

PASSWORD = 'Campus-test-2026!'


@pytest.fixture
def campus(tmp_path):
    settings = Settings(database_url='sqlite:///' + str(tmp_path / 'test.db'),
                        data_dir=tmp_path / 'files', session_secret='test-secret-' * 5, semantic_mode='off')
    app = create_app(settings)
    with ExitStack() as stack:
        # A single lifespan/engine; distinct clients hold separate cookies.
        first = stack.enter_context(TestClient(app, headers={'X-Findly-Request':'1'}))
        clients = [first] + [TestClient(app, headers={'X-Findly-Request':'1'}) for _ in range(4)]
        for client in clients[1:]:
            stack.callback(client.close)
        users = []
        for index, (client, role) in enumerate(zip(clients, ['student','student','security','administrator','lost_property'])):
            response = client.post('/api/auth/register', json=dict(name=f'Campus{index}',surname='Tester',
                email=f'campus{index}@example.com', password=PASSWORD))
            assert response.status_code == 201, response.text
            user = response.json()
            users.append(user)
            if role != 'student':
                with app.state.sessions() as db:
                    db.get(models.User, user['user_id']).role = role
                    db.commit()
        yield dict(app=app, clients=clients, users=users, settings=settings, tmp=tmp_path)


def report(client, kind='lost', **overrides):
    data = dict(title='Black Lenovo laptop sleeve', category='Electronics', colour='Black', brand='Lenovo',
        description='Black padded Lenovo laptop sleeve with a grey logo near the zipper',
        **{'location_'+kind:'Main Campus Library','date_'+kind:'2026-01-02'})
    data.update(overrides)
    response = client.post('/api/reports/'+kind, json=data)
    assert response.status_code == 201, response.text
    return response.json()


def claim(client, found):
    response = client.post('/api/claims', json=dict(found_item_id=found['record_id'],
        claim_statement='This is my laptop sleeve lost in the library.',
        private_description='There is a stitched yellow star inside the left pocket.'))
    assert response.status_code == 201, response.text
    return response.json()
