"""Regression tests for BluePilot issue #193 Ford combo cruise buttons."""

import unittest

from opendbc.car import Bus, structs
from opendbc.sunnypilot.car.ford.carstate_ext import CarStateExt


ButtonType = structs.CarState.ButtonEvent.Type


class _FakeCANParser:
  def __init__(self, vl):
    self.vl = vl


def _cs(cruise_enabled: bool) -> structs.CarState:
  ret = structs.CarState.new_message()
  ret.cruiseState.enabled = cruise_enabled
  return ret


def _parsers(dec_press: int, inc_press: int = 0, cncl_res_press: int = 0, on_off_press: int = 0):
  vl = {
    "Steering_Data_FD1": {
      "CcAslButtnSetDecPress": dec_press,
      "CcAslButtnSetIncPress": inc_press,
      "CcAslButtnCnclResPress": cncl_res_press,
      "CcButtnOnOffPress": on_off_press,
    },
  }
  return {Bus.pt: _FakeCANParser(vl)}


class TestComboButtonEvents(unittest.TestCase):
  def setUp(self):
    self.ext = CarStateExt(structs.CarParams(), structs.CarParamsSP())

  def _events(self):
    return [(event.type, event.pressed) for event in self.ext.button_events]

  def test_sustained_hold_emits_one_press_and_release(self):
    ret = _cs(cruise_enabled=False)

    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1))
    self.assertEqual(self._events(), [(ButtonType.setCruise, True)])

    for _ in range(50):
      self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1))
      self.assertEqual(self._events(), [])

    ret = _cs(cruise_enabled=True)
    for _ in range(20):
      self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1))
      self.assertEqual(self._events(), [])

    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=0))
    self.assertEqual(self._events(), [(ButtonType.setCruise, False)])

  def test_inc_and_dec_do_not_cross_contaminate_setcruise(self):
    ret = _cs(cruise_enabled=False)
    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1, inc_press=0))
    self.assertEqual(self._events(), [(ButtonType.setCruise, True)])

    for _ in range(10):
      self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1, inc_press=0))
      self.assertEqual(self._events(), [])

  def test_tap_while_engaged_emits_decel(self):
    ret = _cs(cruise_enabled=True)
    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=1))
    self.assertEqual(self._events(), [(ButtonType.decelCruise, True)])

    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=0))
    self.assertEqual(self._events(), [(ButtonType.decelCruise, False)])

  def test_cancel_resume_combo_emits_one_pair(self):
    ret = _cs(cruise_enabled=True)
    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=0, cncl_res_press=1))
    self.assertEqual(self._events(), [(ButtonType.cancel, True)])

    for _ in range(10):
      self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=0, cncl_res_press=1))
      self.assertEqual(self._events(), [])

    self.ext.update(ret, structs.CarStateSP(), _parsers(dec_press=0, cncl_res_press=0))
    self.assertEqual(self._events(), [(ButtonType.cancel, False)])


if __name__ == "__main__":
  unittest.main()
