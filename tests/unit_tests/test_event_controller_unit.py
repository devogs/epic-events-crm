# tests/test_event_controller_unit.py
import pytest
import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.controllers.event_controller import create_event, list_events, update_event
from app.models import Contract, Event, Employee, Role

@pytest.fixture
def mock_session():
    return Mock(spec=Session)

@pytest.fixture
def mock_employee():
    return Mock(spec=Employee, id=1, department='Commercial')

@pytest.fixture
def mock_contract():
    return Mock(spec=Contract, id=1, status_signed=True, sales_contact_id=1)

@pytest.fixture
def mock_event():
    return Mock(spec=Event, id=1, contract_id=1, support_contact_id=None, name='Event', 
                attendees=100, event_start=datetime.datetime(2025, 10, 20), 
                event_end=datetime.datetime(2025, 10, 21), location='Venue', notes='Notes')

def test_create_event_commercial_success(mock_session, mock_employee, mock_contract):
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        mock_session.commit.return_value = None
        event = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                             datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert event is not None
        assert event.contract_id == 1
        assert event.name == 'Event'
        assert event.attendees == 100
        assert event.event_start == datetime.datetime(2025, 10, 20)
        assert event.event_end == datetime.datetime(2025, 10, 21)
        assert event.location == 'Venue'
        assert event.notes == 'Notes'
        assert event.support_contact_id is None

def test_create_event_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.event_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied to create events."):
            create_event(mock_session, mock_employee, 1, 'Event', 100, 
                         datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')

def test_create_event_contract_not_found(mock_session, mock_employee):
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert result is None

def test_create_event_unsigned_contract(mock_session, mock_employee):
    mock_contract = Mock(spec=Contract, id=1, status_signed=False, sales_contact_id=1)
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert result is None

def test_create_event_wrong_sales_contact(mock_session, mock_employee, mock_contract):
    mock_contract.sales_contact_id = 2
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert result is None

def test_create_event_invalid_dates(mock_session, mock_employee, mock_contract):
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 21), datetime.datetime(2025, 10, 20), 'Venue', 'Notes')
        assert result is None

def test_create_event_integrity_error(mock_session, mock_employee, mock_contract):
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        mock_session.commit.side_effect = IntegrityError("mock error", {}, None)
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert result is None
        assert mock_session.rollback.called

def test_create_event_unexpected_error(mock_session, mock_employee, mock_contract):
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_contract
        mock_session.commit.side_effect = Exception("unexpected error")
        result = create_event(mock_session, mock_employee, 1, 'Event', 100, 
                              datetime.datetime(2025, 10, 20), datetime.datetime(2025, 10, 21), 'Venue', 'Notes')
        assert result is None
        assert mock_session.rollback.called

def test_list_events_commercial(mock_session, mock_employee):
    mock_event = Mock(spec=Event, id=1, contract_id=1)
    mock_session.query.return_value.options.return_value.join.return_value.filter.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee)
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_support_mine(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=1)
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee, support_filter_scope='mine')
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_support_unassigned(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None)
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee, support_filter_scope='unassigned')
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_support_default(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None)
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee, support_filter_scope='default')
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_support_all_db(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=2)
    mock_session.query.return_value.options.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee, support_filter_scope='all_db')
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_gestion_no_filter(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_event = Mock(spec=Event, id=1, support_contact_id=2)
    mock_session.query.return_value.options.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee)
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_gestion_with_filter(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_event = Mock(spec=Event, id=1, support_contact_id=2)
    mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_event]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        events = list_events(mock_session, mock_employee, filter_by_support_id=2)
        assert len(events) == 1
        assert events[0] == mock_event

def test_list_events_permission_denied(mock_session, mock_employee):
    with patch('app.controllers.event_controller.check_permission', return_value=False):
        with pytest.raises(PermissionError, match="Permission denied to view events."):
            list_events(mock_session, mock_employee)

def test_update_event_support_success(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=1, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_event
    mock_session.commit.return_value = None
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        updated = update_event(mock_session, mock_employee, 1, 
                              name='New Event', attendees=200, 
                              event_start=datetime.datetime(2025, 10, 22), 
                              event_end=datetime.datetime(2025, 10, 23), location='New Venue', notes='New Notes')
        assert updated is not None
        assert updated.name == 'New Event'
        assert updated.attendees == 200
        assert updated.event_start == datetime.datetime(2025, 10, 22)
        assert updated.event_end == datetime.datetime(2025, 10, 23)
        assert updated.location == 'New Venue'
        assert updated.notes == 'New Notes'

def test_update_event_support_unassigned(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=2, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_event
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, name='New Event')
        assert result is None

def test_update_event_not_found(mock_session, mock_employee):
    mock_employee.department = 'Gestion'
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = None
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, name='New Event')
        assert result is None

def test_update_event_invalid_contract(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_event)))),
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=None))))
    ]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, contract_id=2)
        assert result is None

def test_update_event_unsigned_contract(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_contract = Mock(spec=Contract, id=2, status_signed=False)
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_event)))),
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_contract))))
    ]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, contract_id=2)
        assert result is None

def test_update_event_invalid_support_contact(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Gestion')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_event)))),
        Mock(filter=Mock(return_value=Mock(one_or_none=Mock(return_value=None))))
    ]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, support_contact_id=3)
        assert result is None

def test_update_event_support_assign_other(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=None, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.side_effect = [
        Mock(filter_by=Mock(return_value=Mock(one_or_none=Mock(return_value=mock_event)))),
        Mock(filter=Mock(return_value=Mock(one_or_none=Mock(return_value=Mock(id=2)))))
    ]
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, support_contact_id=2)
        assert result is None

def test_update_event_invalid_dates(mock_session):
    mock_employee = Mock(spec=Employee, id=1, department='Support')
    mock_event = Mock(spec=Event, id=1, support_contact_id=1, 
                     event_start=datetime.datetime(2025, 10, 20), event_end=datetime.datetime(2025, 10, 21))
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_event
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        result = update_event(mock_session, mock_employee, 1, 
                              event_start=datetime.datetime(2025, 10, 21), 
                              event_end=datetime.datetime(2025, 10, 20))
        assert result is None

def test_update_event_no_updates(mock_session, mock_employee):
    mock_employee.department = 'Gestion'
    mock_session.query.return_value.filter_by.return_value.one_or_none.return_value = mock_event
    with patch('app.controllers.event_controller.check_permission', return_value=True):
        updated = update_event(mock_session, mock_employee, 1)
        assert updated is mock_event
        assert not mock_session.commit.called