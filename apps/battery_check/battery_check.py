import datetime

import hassapi as hass

def state_le_threshold(threshold, state):
    try:
        return int(state) < threshold
    except:
        return False

def state_gte_threshold(threshold, state):
    try:
        return int(state) >= threshold
    except:
        return False


class BatteryCheck(hass.Hass):

    async def initialize(self):
        self.timer_handle_list = []
        self.listen_event_handle_list = []
        self.listen_state_handle_list = []
        self.registered_entity_callbacks = {}

        if 'threshold' not in self.args:
            self.log('threshold set, not setting up notifiers...', level='ERROR')
            return
        self.log(f'threshold: {self.args["threshold"]}')

        if 'notify_hour_start_hour' not in self.args:
            self.log('notify_hour_start_hour not set, not setting up notifiers...', level='ERROR')
            return
        self.log(f'notify_hour_start_hour: {self.args["notify_hour_start_hour"]}')

        if 'notify_hour_end_hour' not in self.args:
            self.log('notify_hour_end_hour not set, not setting up notifiers...', level='ERROR')
            return
        self.log(f'notify_hour_end_hour: {self.args["notify_hour_end_hour"]}')

        await self.register_battery_notifications()
        self.timer_handle_list.append(
            await self.run_daily(self.register_battery_notifications, datetime.time(12, 0, 0))
        )

    async def terminate(self):
        for timer_handle in self.timer_handle_list:
            await self.cancel_timer(timer_handle)

        for listen_event_handle in self.listen_event_handle_list:
            await self.cancel_listen_event(listen_event_handle)

        for listen_state_handle in self.listen_state_handle_list:
            await self.cancel_listen_state(listen_state_handle)

        for callback_handles in filter(None, self.registered_entity_callbacks.values()):
            await self.cancel_timer(listen_state_handle)

    async def register_battery_notifications(self, *args, **kwargs):
        """Register battery notifications"""

        sensors = await self.get_state("sensor")
        batteries = (
            v for k, v in sensors.items() 
            if v.get('attributes', {}).get('device_class') == 'battery'
            and v.get('attributes', {}).get('battery_type') is not None
            and k not in self.registered_entity_callbacks
        )
        for battery in batteries:
            self.log(f'Registering battery: {battery["entity_id"]}')

            self.registered_entity_callbacks[battery['entity_id']] = None
            self.listen_state_handle_list.append(await self.listen_state(
                self.notify_battery_low, 
                battery['entity_id'], 
                constrain_state=lambda state: state_le_threshold(self.args['threshold'], state)
            ))
            self.listen_state_handle_list.append(await self.listen_state(
                self.cancel_notify_battery_low, 
                battery['entity_id'], 
                constrain_state=lambda state: state_gte_threshold(self.args['threshold'], state)
            ))

    async def notify_battery_low(self, entity, attribute, old, new, kwargs):
        """Notify battery low immediately, or schedule it depending on time"""
        self.log(f'Notify for: {entity}')
        friendly_name = await self.get_state(entity, attribute='friendly_name')
        battery_type = await self.get_state(entity, attribute='battery_type')

        title = f'{friendly_name} is low at {new}%!'
        message = f'Replace with {battery_type}.'

        if await self.now_is_between(f'{self.args["notify_hour_start_hour"]}:00:00', f'{self.args["notify_hour_end_hour"]}:00:00'):
            self.log(f'Executing notification: {title} {message}')
            await self._maybe_cancel_entity_timer(entity)
            await self.run_in(self.send_notify, 0, message=message, title=title)
        else:
            self.log(f'Scheduling notification for {self.args["notify_hour_start_hour"]}:00:00 - {title} {message}')
            await self._maybe_cancel_entity_timer(entity)
            self.registered_entity_callbacks[entity] = await self.run_once(
                self.send_notify, 
                datetime.time(self.args['notify_hour_start_hour'], 0, 0), 
                message=message, 
                title=title
            )

    async def cancel_notify_battery_low(self, entity, attribute, old, new, kwargs):
        """Cancel any pending notifications"""

        await self._maybe_cancel_entity_timer(entity)

    async def _maybe_cancel_entity_timer(self, entity):
        if self.registered_entity_callbacks[entity] is not None:
            friendly_name = await self.get_state(entity, attribute='friendly_name')
            self.log(f'Cancelling notification for {friendly_name}...')

            await self.cancel_timer(self.registered_entity_callbacks[entity])
            self.registered_entity_callbacks[entity] = None

    async def send_notify(self, kwargs):
        self.notify(kwargs['message'], title=kwargs['title'], name="mike_phone")
