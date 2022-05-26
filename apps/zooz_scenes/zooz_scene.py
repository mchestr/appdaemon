import datetime

import aiohttp
import hassapi as hass
from appdaemon.exceptions import TimeOutException


class ZoozScene(hass.Hass):
    PRESS_STATES = ("0", "3", "4", "5", "6")
    HELD_STATE = "2"
    RELEASED_STATE = "1"
    SCENES = [
        'scene_up_held',
        'scene_up_released',
        'scene_up_1', 
        'scene_up_2', 
        'scene_up_3', 
        'scene_up_4', 
        'scene_up_5', 
        'scene_down_held',
        'scene_down_released',
        'scene_down_1', 
        'scene_down_2', 
        'scene_down_3', 
        'scene_down_4', 
        'scene_down_5'
    ]
    ACTION_UP = 'up'
    ACTION_DOWN = 'down'

    LED_WHITE = "0"
    LED_BLUE = "1"
    LED_GREEN = "2"
    LED_RED = "3"

    async def initialize(self):
        self.timer_handle_list = []
        self.listen_event_handle_list = []
        self.listen_state_handle_list = []
        self.implemented_scenes = []
        self.led_color_before = self.args.get('led_color_before', self.LED_RED)
        self.led_color_after = self.args.get('led_color_after', self.LED_BLUE)

        if 'light' not in self.args:
            self.log('light not set in scene', level='ERROR')
            return
        self.light = self.args['light']
        if 'node_name' not in self.args:
            self.log('node_name not set in scene', level='ERROR')
            return
        self.node_name = self.args['node_name']
        
        scene_up_entity_id = f'sensor.{self.light.split(".")[1]}_scene_state_scene_001'
        scene_down_entity_id = f'sensor.{self.light.split(".")[1]}_scene_state_scene_002'

        self.log(f'Setting up scene triggers for {self.light}')
        self.listen_state_handle_list.append(
            await self.listen_state(
                self.scene_triggered,
                scene_up_entity_id,
                action=self.ACTION_UP
            )
        )
        self.listen_state_handle_list.append(
            await self.listen_state(
                self.scene_triggered,
                scene_down_entity_id,
                action=self.ACTION_DOWN
            )
        )

    async def terminate(self):
        for timer_handle in self.timer_handle_list:
            await self.cancel_timer(timer_handle)

        for listen_event_handle in self.listen_event_handle_list:
            await self.cancel_listen_event(listen_event_handle)

        for listen_state_handle in self.listen_state_handle_list:
            await self.cancel_listen_state(listen_state_handle)
    
    async def scene_triggered(self, entity, attribute, old, new, kwargs):
        if not new:
            return
        
        scene = self._state_to_scene(kwargs['action'], new)
        if not scene:
            self.log(f'unknown scene triggered: entity={entity}, old={old}, new={new}, kwargs={kwargs}', level='ERROR')
            return
        func = getattr(self, scene, None)
        if not func:
            self.log(f'{scene} not implemented, skipping...')
            return

        self.log(f'{scene} triggered on {entity}')
        await self.before_func(entity, attribute, old, new, kwargs)
        try:
            await func(entity, attribute, old, new, kwargs)
        finally:
            await self.after_func(entity, attribute, old, new, kwargs)

    async def before_func(self, entity, attribute, old, new, kwargs):
        await self.call_service(
            'mqtt/publish',
            topic=f'zwave/{self.node_name}/112/0/2/set',
            payload='3'
        )
        await self.call_service(
            'mqtt/publish',
            topic=f'zwave/{self.node_name}/112/0/14/set',
            payload=self.led_color_before
        )

    async def after_func(self, entity, attribute, old, new, kwargs):
        await self.call_service(
            'mqtt/publish',
            topic=f'zwave/{self.node_name}/112/0/2/set',
            payload='0'
        )
        await self.call_service(
            'mqtt/publish',
            topic=f'zwave/{self.node_name}/112/0/14/set',
            payload=self.led_color_after
        )

    def _state_to_scene(self, action, state):
        if state in self.PRESS_STATES:
            return f'scene_{action}_{self.PRESS_STATES.index(state) + 1}'
        if state == self.HELD_STATE:
            return f'scene_{action}_held'
        if state == self.RELEASED_STATE:
            return f'scene_{action}_released'


class OfficeLightSwitchScene(ZoozScene):

    async def scene_up_2(self, entity, attribute, old, new, kwargs):
        self.log('office_light_switch_scene.scene_up_2 called')
        await self.call_service(
            'cover/set_cover_position',
            position=100,
            entity_id='cover.desk'
        )
        await self.sleep(2)
        desk = self.get_entity('cover.desk')
        try:
            await desk.wait_state("open", timeout=30)
        except TimeOutException:
            self.log('desk did not complete in time')

    async def scene_down_2(self, entity, attribute, old, new, kwargs):
        self.log('office_light_switch_scene.scene_down_2 called')
        await self.call_service(
            'cover/set_cover_position',
            position=26,
            entity_id='cover.desk'
        )
        await self.sleep(2)
        desk = self.get_entity('cover.desk')
        try:
            await desk.wait_state("open", timeout=30)
        except TimeOutException:
            self.log('desk did not complete in time', level='ERROR')


class MasterBedroomLightSwitchScene(ZoozScene):

    async def scene_up_2(self, entity, attribute, old, new, kwargs):
        self.log('master_bedroom_light_switch_scene.scene_up_2 called')
        await self.turn_on('group.master_bathroom_lights')
        await self.turn_on('group.master_bedroom_lights')

    scene_up_3 = scene_up_2
    scene_up_4 = scene_up_2

    async def scene_down_2(self, entity, attribute, old, new, kwargs):
        self.log('master_bedroom_light_switch_scene.scene_down_2 called')
        await self.turn_off('group.master_bathroom_lights')
        await self.turn_off('group.master_bedroom_lights')

    scene_down_3 = scene_down_2
    scene_down_4 = scene_down_2
    
    async def before_func(self, *args, **kwargs):
        pass

    async def after_func(self, *args, **kwargs):
        pass


class EntryLightSwitchScene(ZoozScene):

    async def scene_down_2(self, entity, attribute, old, new, kwargs):
        self.log('entry_light_switch_scene.scene_down_2 called')
        await self.sleep(30)
        await self.turn_off('group.all_lights')

        group_all = self.get_entity('group.all_lights')
        try:
            await group_all.wait_state("off", timeout=30)
        except TimeOutException:
            self.log('timed out waiting for state', level='ERROR')

    scene_down_held = scene_down_2
    scene_down_3 = scene_down_2
    scene_down_4 = scene_down_2
