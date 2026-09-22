from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ClimateLog, Greenhouse, IrrigationCycle, Zone

User = get_user_model()


def climate_payload(zone_id, **overrides):
    payload = {
        "zoneId": zone_id,
        "recordedAt": timezone.now().isoformat(),
        "tempC": "24.50",
        "humidityPct": "65.00",
        "parUmol": "300.00",
        "co2Ppm": "600.00",
    }
    payload.update(overrides)
    return payload


def irrigation_payload(zone_id, **overrides):
    payload = {
        "zoneId": zone_id,
        "startAt": timezone.now().isoformat(),
        "durationMin": 30,
        "waterLiters": "100.00",
        "status": "scheduled",
    }
    payload.update(overrides)
    return payload


class ZonePauseTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="x", role=User.ROLE_ADMIN
        )
        self.grower = User.objects.create_user(
            username="grower", password="x", role=User.ROLE_GROWER
        )
        self.gh = Greenhouse.objects.create(name="测试棚")
        self.zone = Zone.objects.create(
            greenhouse=self.gh, zone_code="A-01", status=Zone.STATUS_GROWING
        )
        self.other = Zone.objects.create(
            greenhouse=self.gh, zone_code="A-02", status=Zone.STATUS_IDLE
        )

    # ---- 模型/列表 ----
    def test_new_zone_defaults_to_not_paused(self):
        self.assertFalse(self.zone.is_paused)

    def test_list_includes_paused_zones_and_flag(self):
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        resp = self.client.get(reverse("zone-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"] if "results" in resp.data else resp.data
        self.assertEqual(len(rows), 2)
        flags = {r["zoneCode"]: r["isPaused"] for r in rows}
        self.assertTrue(flags["A-01"])
        self.assertFalse(flags["A-02"])

    def test_is_paused_is_read_only_on_create_and_update(self):
        self.client.force_authenticate(self.grower)
        resp = self.client.post(
            reverse("zone-list"),
            {
                "greenhouseId": self.gh.id,
                "zoneCode": "A-09",
                "cropName": "",
                "status": "idle",
                "isPaused": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(Zone.objects.get(zone_code="A-09").is_paused)

        resp = self.client.patch(
            reverse("zone-detail", args=[self.zone.id]),
            {"isPaused": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["isPaused"])
        self.zone.refresh_from_db()
        self.assertFalse(self.zone.is_paused)

    # ---- 权限 ----
    def test_grower_cannot_pause(self):
        self.client.force_authenticate(self.grower)
        resp = self.client.post(reverse("zone-pause", args=[self.zone.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.zone.refresh_from_db()
        self.assertFalse(self.zone.is_paused)

    def test_grower_cannot_resume(self):
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        resp = self.client.post(reverse("zone-resume", args=[self.zone.id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.zone.refresh_from_db()
        self.assertTrue(self.zone.is_paused)

    def test_anonymous_pause_is_unauthorized(self):
        resp = self.client.post(reverse("zone-pause", args=[self.zone.id]))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_pause_and_resume_roundtrip(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(reverse("zone-pause", args=[self.zone.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data,
            {"id": self.zone.id, "zoneCode": "A-01", "isPaused": True},
        )
        self.zone.refresh_from_db()
        self.assertTrue(self.zone.is_paused)

        resp = self.client.post(reverse("zone-resume", args=[self.zone.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["isPaused"], False)
        self.zone.refresh_from_db()
        self.assertFalse(self.zone.is_paused)

    # ---- 暂停区写入限制 ----
    def test_create_climate_in_paused_zone_conflicts(self):
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        resp = self.client.post(
            reverse("climate-log-list"), climate_payload(self.zone.id), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("暂停", str(resp.data["detail"]))
        self.assertIn("禁止新建", str(resp.data["detail"]))
        self.assertEqual(ClimateLog.objects.filter(zone=self.zone).count(), 0)

    def test_create_irrigation_in_paused_zone_conflicts(self):
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        resp = self.client.post(
            reverse("irrigation-cycle-list"),
            irrigation_payload(self.zone.id),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("暂停", str(resp.data["detail"]))
        self.assertEqual(IrrigationCycle.objects.filter(zone=self.zone).count(), 0)

    def test_create_climate_in_active_zone_ok(self):
        self.client.force_authenticate(self.grower)
        resp = self.client.post(
            reverse("climate-log-list"), climate_payload(self.zone.id), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_update_existing_climate_in_paused_zone_still_allowed(self):
        self.zone.is_paused = True
        self.zone.save()
        log = ClimateLog.objects.create(
            zone=self.zone,
            recorded_at=timezone.now(),
            temp_c=Decimal("20.00"),
            humidity_pct=Decimal("60.00"),
        )
        self.client.force_authenticate(self.grower)
        resp = self.client.put(
            reverse("climate-log-detail", args=[log.id]),
            climate_payload(self.zone.id, tempC="26.00"),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        log.refresh_from_db()
        self.assertEqual(log.temp_c, Decimal("26.00"))

    def test_update_existing_irrigation_in_paused_zone_still_allowed(self):
        self.zone.is_paused = True
        self.zone.save()
        cyc = IrrigationCycle.objects.create(
            zone=self.zone,
            start_at=timezone.now(),
            duration_min=30,
            water_liters=Decimal("100.00"),
        )
        self.client.force_authenticate(self.grower)
        resp = self.client.put(
            reverse("irrigation-cycle-detail", args=[cyc.id]),
            irrigation_payload(self.zone.id, durationMin=45),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cyc.refresh_from_db()
        self.assertEqual(cyc.duration_min, 45)

    def test_update_climate_cannot_move_into_paused_zone(self):
        self.other.is_paused = True
        self.other.save()
        log = ClimateLog.objects.create(
            zone=self.zone,
            recorded_at=timezone.now(),
            temp_c=Decimal("20.00"),
            humidity_pct=Decimal("60.00"),
        )
        self.client.force_authenticate(self.grower)
        resp = self.client.put(
            reverse("climate-log-detail", args=[log.id]),
            climate_payload(self.other.id),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("暂停", str(resp.data["detail"]))
        log.refresh_from_db()
        self.assertEqual(log.zone_id, self.zone.id)

    def test_update_irrigation_cannot_move_into_paused_zone(self):
        self.other.is_paused = True
        self.other.save()
        cyc = IrrigationCycle.objects.create(
            zone=self.zone,
            start_at=timezone.now(),
            duration_min=30,
            water_liters=Decimal("100.00"),
        )
        self.client.force_authenticate(self.admin)
        resp = self.client.put(
            reverse("irrigation-cycle-detail", args=[cyc.id]),
            irrigation_payload(self.other.id),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        cyc.refresh_from_db()
        self.assertEqual(cyc.zone_id, self.zone.id)

    def test_update_climate_between_active_zones_ok(self):
        log = ClimateLog.objects.create(
            zone=self.zone,
            recorded_at=timezone.now(),
            temp_c=Decimal("20.00"),
            humidity_pct=Decimal("60.00"),
        )
        self.client.force_authenticate(self.grower)
        resp = self.client.patch(
            reverse("climate-log-detail", args=[log.id]),
            {"zoneId": self.other.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        log.refresh_from_db()
        self.assertEqual(log.zone_id, self.other.id)

    # ---- 仪表盘 ----
    def test_dashboard_paused_count_matches_paused_zones(self):
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data["pausedZoneCount"],
            Zone.objects.filter(is_paused=True).count(),
        )
        self.assertEqual(resp.data["pausedZoneCount"], 1)

    def test_existing_data_of_paused_zone_still_queryable(self):
        log = ClimateLog.objects.create(
            zone=self.zone,
            recorded_at=timezone.now(),
            temp_c=Decimal("20.00"),
            humidity_pct=Decimal("60.00"),
        )
        cyc = IrrigationCycle.objects.create(
            zone=self.zone,
            start_at=timezone.now(),
            duration_min=30,
            water_liters=Decimal("100.00"),
        )
        self.zone.is_paused = True
        self.zone.save()
        self.client.force_authenticate(self.grower)
        c = self.client.get(
            reverse("climate-log-list"), {"zoneId": self.zone.id}
        )
        i = self.client.get(
            reverse("irrigation-cycle-list"), {"zoneId": self.zone.id}
        )
        self.assertEqual(c.data["results"][0]["id"], log.id)
        self.assertEqual(i.data["results"][0]["id"], cyc.id)
