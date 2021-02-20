
import datetime
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_call_later

import logging
_LOGGER = logging.getLogger(__name__)


DOMAIN = 'zhiact'

ACTUATE_SCHEMA = vol.Schema({
    vol.Required('sensor_id'): cv.string,
    vol.Optional('sensor_attr'): cv.string,
    vol.Required('sensor_values'): list,
    vol.Optional('alt_sensor_values'): list,
    vol.Optional('alt_time_range'): list,
    vol.Required('entity_id'): cv.string,
    vol.Optional('entity_attr'): cv.string,
    vol.Optional('service'): cv.string,
    vol.Optional('service_attr'): cv.string,
    vol.Required('entity_values'): list,
    vol.Optional('condition_attr'): cv.string,
    vol.Optional('condition_values'): list,
    vol.Optional('delay'): int,
})

_hass = None
_executors = {}


def execute(params):
    # Get entity state
    entity_id = params.get('entity_id')
    domain = entity_id[:entity_id.find('.')]

    state = _hass.states.get(entity_id)
    if state is None:
        _LOGGER.error("Entity %s error", sensor_id)
        return
    state_value = state.state
    state_attributes = state.attributes

    # Check condition
    condition_attr = params.get('condition_attr')
    if condition_attr is not None:
        condition_value = state_value if condition_attr == 'STATE' else state_attributes.get(
            condition_attr)
        if condition_value is None:
            #_LOGGER.debug('Check condition: condition_value is None')
            return
        condition_values = params.get('condition_values')
        if condition_values is not None and condition_value not in condition_values:
            #_LOGGER.debug('Check condition: %s not in %s', condition_value, condition_values)
            return

    # Get sensor state
    sensor_id = params.get('sensor_id')
    sensor_attr = params.get('sensor_attr')

    alt_time_range = params.get('alt_time_range') or [20, 8]
    if 'alt_sensor_values' in params:
        hour = datetime.datetime.now().hour
        if alt_time_range[1] > alt_time_range[0]:
            alt_time = hour >= alt_time_range[0] and hour < alt_time_range[1]
        else:
            alt_time = hour >= alt_time_range[0] or hour < alt_time_range[1]
    else:
        alt_time = False
    sensor_values = params.get(
        'alt_sensor_values' if alt_time else 'sensor_values')

    sensor_state = _hass.states.get(sensor_id)
    try:
        sensor_attributes = sensor_state.attributes
        sensor_value = sensor_state.state if sensor_attr is None else sensor_attributes.get(
            sensor_attr)
        sensor_number = float(sensor_value)
    except:
        _LOGGER.error("Sensor %s %s error", sensor_id, sensor_attr or '')
        return

    # Log prefix
    sensor_log = sensor_attributes.get('friendly_name')
    if sensor_attr:
        sensor_log += '.' + sensor_attr
    sensor_log += '=' + str(sensor_value)

    # Action params
    entity_attr = params.get('entity_attr')
    service_attr = params.get('service_attr') or entity_attr
    service = params.get('service') or 'set_' + service_attr
    entity_values = params.get('entity_values')
    entity_log = state_attributes.get('friendly_name')

    # Check sensor range
    i = len(sensor_values) - 1
    while i >= 0:
        if sensor_number >= sensor_values[i]:
            sensor_log += '≥' + str(sensor_values[i])
            from_value = state_value if entity_attr is None else state_attributes.get(
                entity_attr)
            to_value = entity_values[i]

            if entity_attr:
                entity_log += '.' + entity_attr
            entity_log += '=' + str(from_value)

            if state_value == 'off':
                entity_log += ', ⇒on'
                _hass.services.call(domain, 'turn_on', {
                                    'entity_id': entity_id}, True)

            if from_value == to_value:
                _LOGGER.debug('%s; %s', sensor_log, entity_log)
                return

            pos = service.find('.')
            if pos != -1:
                domain = service[:pos]
                service = service[pos + 1:]
            data = {'entity_id': entity_id,
                    service_attr or entity_attr: to_value}
            _LOGGER.warn('%s; %s, %s⇒%s', sensor_log,
                         entity_log, service, to_value)
            _hass.services.call(domain, service, data, True)
            return
        else:
            i = i - 1

    # Turn off
    sensor_log += '<' + str(sensor_values[0])
    if state_value == 'off':
        _LOGGER.debug('%s, %s=off', sensor_log, entity_log)
        return

    # Log
    _LOGGER.warn('%s, %s=%s, ⇒off', sensor_log, entity_log, state_value)
    _hass.services.call(domain, 'turn_off', {'entity_id': entity_id}, True)


class DelayExecutor:

    def __init__(self, key, delay, params):
        self.key = key
        self.params = params
        async_call_later(_hass, delay, self.call)

    def call(self, *_):
        del _executors[self.key]
        execute(self.params)


def actuate(call):
    params = call.data
    delay = params.get('delay')
    if delay is None:
        delay = 120
    if delay > 0:
        key = params['entity_id'] + '~' + \
            (params.get('service_attr') or params.get('entity_attr'))
        if key not in _executors:
            _executors[key] = DelayExecutor(key, delay, params)
        # else:
        #    _LOGGER.debug('%s ignored', key)
    else:
        execute(params)


def setup(hass, config):
    global _hass
    _hass = hass
    hass.services.register(DOMAIN, 'actuate', actuate, schema=ACTUATE_SCHEMA)
    return True
