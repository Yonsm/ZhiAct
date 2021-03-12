# [https://github.com/Yonsm/ZhiAct](https://github.com/Yonsm/ZhiAct)

Actuating Service Automatically for HomeAssistant

根据传感器的数值区间，来自动化设定执行设备的各种状态。

和直接用原生的 automation+jinja2 写比起来，`ZhiAct` 写起来太简单了（之前用 jinja2 写出来的规则，真是受够了；`appdaemon` 这种半成品也是）。另外，`ZhiAct` 检查设备当前状态，除非必要，不会轻易重复设定设备状态。

## 1. 安装准备

把 `zhiact` 放入 `custom_components`；也支持在 [HACS](https://hacs.xyz/) 中添加自定义库的方式安装。

## 2. 配置方法

参见 [我的 Home Assistant 配置](https://github.com/Yonsm/.homeassistant) 中 [configuration.yaml](https://github.com/Yonsm/.homeassistant/blob/main/configuration.yaml)

```yaml
zhiact:
```

参数说明直接看 [services.yaml](https://github.com/Yonsm/ZhiAct/blob/main/custom_components/zhiact/services.yaml) 的描述。

## 3. 使用方式

举个例子，根据温度来控制空调档位：

```yaml
- alias: 书房空调温度变化
  trigger:
    - platform: time
      at: '21:00:01'
    - platform: state
      entity_id: sensor.fan_temperature
  condition:
    - condition: time
      after: '20:30'
      before: '07:20'
  action:
    - service: zhiact.actuate
      data:
        sensor_id: sensor.fan_temperature
        sensor_values: [27.5, 28.5, 32, 34]
        alt_sensor_values: [28.5, 29, 32, 34]
        alt_time_range: [2, 7]
        entity_id: climate.mitsubishi
        entity_attr: fan_mode
        entity_values: [low, mid, high, highest]
```

控制出来的温度曲线呈锯齿状，后半夜 2-7 点的控温规则高一点：

![PREVIEW](https://github.com/Yonsm/ZhiAct/blob/main/PREVIEW.jpg)

`HomeAssistant` 越改越作死，连空调的开关状态都没有历史可查了。我们可以在 `configuration.yaml` 里面做如下配置，可以方便看一整天下来空调所处的模式：

```yaml
sensors:
  - platform: template
    sensors:
      mitsubishi_mode:
        friendly_name: 书房空调模式
        value_template: '{% set mode = state_attr("climate.mitsubishi", "fan_mode") %}{% if is_state("climate.mitsubishi", "off") %}off{% elif mode == "low" %}一{% elif mode == "mid" %}二{% elif mode == "high" %}三{% elif mode == "highest" %}四{% else %}{{ mode }}{% endif %}'
```

类似地，也可以用根据 PM2.5 控制净化器、根据 CO2 控制新风机等。更多例子，参考我的 [co2.yaml](https://github.com/Yonsm/.homeassistant/blob/main/automations/co2.yaml)、[pm25.yaml](https://github.com/Yonsm/.homeassistant/blob/main/automations/pm25.yaml)、[temperature.yaml](https://github.com/Yonsm/.homeassistant/blob/main/automations/temperature.yaml)。

## 4. 参考

- [Yonsm.NET](https://yonsm.github.io)
- [Hassbian.com](https://bbs.hassbian.com/thread-7876-1-1.html)
- [Yonsm's .homeassistant](https://github.com/Yonsm/.homeassistant)
