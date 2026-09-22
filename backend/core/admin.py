from django.contrib import admin

from .models import ClimateLog, Greenhouse, IrrigationCycle, Zone


@admin.register(Greenhouse)
class GreenhouseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "location", "area_m2")
    search_fields = ("name", "location")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "greenhouse", "zone_code", "crop_name", "status", "is_paused")
    list_filter = ("status", "is_paused", "greenhouse")
    search_fields = ("zone_code", "crop_name")
    list_editable = ("is_paused",)


@admin.register(ClimateLog)
class ClimateLogAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "recorded_at", "temp_c", "humidity_pct", "par_umol", "co2_ppm")
    list_filter = ("zone",)


@admin.register(IrrigationCycle)
class IrrigationCycleAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "start_at", "duration_min", "water_liters", "status")
    list_filter = ("status", "zone")
