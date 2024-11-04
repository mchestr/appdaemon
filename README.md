# AppDaemon Config [Deprecated]

Deprecated: I no longer use these automations and instead rely on home assistant blueprints & automations for similar functionality.

[AppDaemon](https://appdaemon.readthedocs.io/en/latest/) running on [my Kubernetes cluster](https://github.com/mchestr/home-cluster).  This configuration is read and persisted within AppDaemon.

## Automations

All automations are written using AppDaemon in asynchronous mode, which means no threads, and async syntax is used.

Only a couple automations are done via AppDaemon as I prefer to keep most things within Home Assistant, however, some automations are just way more
complex when written in YAML.

### Battery Check

[Battery Check](./apps/battery_check/) is a simple automation that will find all batteries and send notifications when they are getting low.

### Zooz Scenes

[Zooz Scenes](./apps/zooz_scenes/) is an automation used to trigger different scenes for [Zooz](https://www.getzooz.com/) Z-Wave switches ([Amazon Affiliate Link](https://amzn.to/3LCaO2b)). Most of the switches in our home are these types of switches. Writing this in Python seemed easier than creating a blueprint in Home Assistant.
