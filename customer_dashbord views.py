


from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_GET
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from .models import CustomerWasteInfo, CustomerPickupDate, CustomerLocationHistory
from super_admin_dashboard.models import State, District, LocalBody, LocalBodyCalendar
from .utils import is_customer


# Role checking
class CustomerRoleRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 0


@login_required
def customer_dashboard(request):
    if request.user.role != 0:
        return redirect('authentication:login')
    return render(request, 'customer_dashboard.html')


@login_required
@user_passes_test(is_customer)
def waste_profile_list(request):
    profiles = CustomerWasteInfo.objects.filter(user=request.user)
    return render(request, "waste_profile_list.html", {"profiles": profiles})


@login_required
@user_passes_test(is_customer)
def waste_profile_detail(request, pk):
    info = get_object_or_404(CustomerWasteInfo, pk=pk, user=request.user)
    selected_dates = CustomerPickupDate.objects.filter(user=request.user).values_list("localbody_calendar__date", flat=True)

    # Get location history for this waste info
    location_history = CustomerLocationHistory.objects.filter(waste_info=info).order_by('-changed_at')[:5]

    return render(request, "waste_profile_detail.html", {
        "info": info,
        "selected_dates": selected_dates,
        "location_history": location_history,
    })



def get_ward_names():
    """Return a dictionary mapping ward numbers to ward names"""
    return {
        1: "Fort Kochi",
        2: "Kalvathy",
        3: "Earavely",
        4: "Karippalam",
        5: "Cheralayi",
        6: "Mattanchery",
        7: "Chakkamadam",
        8: "Karuvelippady",
        9: "Island North",
        10: "Ravipuram",
        11: "Ernakulam South",
        12: "Gandhi Nagar",
        13: "Kathrikadavu",
        14: "Ernakulam Central",
        15: "Ernakulam North",
        16: "Kaloor South",
        17: "Kaloor North",
        18: "Thrikkanarvattom",
        19: "Ayyappankavu",
        20: "Pottakuzhy",
        21: "Elamakkara South",
        22: "Pachalam",
        23: "Thattazham",
        24: "Vaduthala West",
        25: "Vaduthala East",
        26: "Elamakkara North",
        27: "Puthukkalavattam",
        28: "Kunnumpuram",
        29: "Ponekkara",
        30: "Edappally",
        31: "Changampuzha",
        32: "Dhevankulangara",
        33: "Palarivattom",
        34: "Stadium",
        35: "Karanakkodam",
        36: "Puthiyaroad",
        37: "Padivattam",
        38: "Vennala",
        39: "Chakkaraparambu",
        40: "Chalikkavattam",
        41: "Thammanam",
        42: "Elamkulam",
        43: "Girinagar",
        44: "Ponnurunni",
        45: "Ponnurunni East",
        46: "Vyttila",
        47: "Poonithura",
        48: "Vyttila Janatha",
        49: "Kadavanthra",
        50: "Panampilly Nagar",
        51: "Perumanoor",
        52: "Konthuruthy",
        53: "Thevara",
        54: "Island South",
        55: "Kadebhagam",
        56: "Palluruthy East",
        57: "Thazhuppu",
        58: "Eadakochi North",
        59: "Edakochi South",
        60: "Perumbadappu",
        61: "Konam",
        62: "Palluruthy Kacheripady",
        63: "Nambyapuram",
        64: "Palluruthy",
        65: "Pullardesam",
        66: "Tharebhagam",
        67: "Thoppumpady",
        68: "Mundamvely East",
        69: "Mundamvely",
        70: "Manassery",
        71: "Moolamkuzhy",
        72: "Chullickal",
        73: "Nasrathu",
        74: "Panayappilly",
        75: "Amaravathy",
        76: "Fortkochi Veli"
    }

def get_ward_options():
    """Return a list of tuples (number, name) for ward options"""
    ward_names = get_ward_names()
    return [(i, ward_names.get(i, f'Ward {i}')) for i in range(1, 74)]



def validate_coordinates(latitude, longitude):
    """Validate latitude and longitude values"""
    try:
        if latitude and longitude:
            lat = Decimal(latitude)
            lng = Decimal(longitude)

            # Check valid range
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng
    except (InvalidOperation, ValueError, TypeError):
        pass

    return None, None


@login_required
@user_passes_test(lambda u: u.role == 0)
def waste_profile_create(request):
    states = State.objects.all()
    ward_range = range(1, 75)
    bag_range = range(1, 11)
    ward_options = get_ward_options()

    if request.method == "POST":
        # Get and validate coordinates
        latitude_raw = request.POST.get("latitude")
        longitude_raw = request.POST.get("longitude")
        latitude, longitude = validate_coordinates(latitude_raw, longitude_raw)

        # Create waste info with location data
        info = CustomerWasteInfo.objects.create(
            user=request.user,
            full_name=request.POST.get("full_name"),
            secondary_number=request.POST.get("secondary_number"),
            pickup_address=request.POST.get("pickup_address"),
            landmark=request.POST.get("landmark"),
            latitude=latitude,
            longitude=longitude,
            state_id=request.POST.get("state"),
            district_id=request.POST.get("district"),
            localbody_id=request.POST.get("localbody"),
            ward=request.POST.get("ward"),
            number_of_bags=request.POST.get("number_of_bags"),
            waste_type=request.POST.get("waste_type"),
            comments=request.POST.get("comments"),
            pincode=request.POST.get("pincode")
        )

        # Save location history if coordinates provided
        if latitude and longitude:
            CustomerLocationHistory.objects.create(
                waste_info=info,
                latitude=latitude,
                longitude=longitude,
                changed_by=request.user
            )
            messages.success(request, "Waste profile created with location tracking!")
        else:
            messages.warning(request, "Waste profile created without location data. Please update location later.")

        # Handle pickup dates (multiple selection)
        selected_date_ids = request.POST.get("selected_date", "")
        if selected_date_ids:
            date_ids = [int(id_str) for id_str in selected_date_ids.split(',') if id_str.isdigit()]
            # Limit to 4 bookings
            date_ids = date_ids[:4]

            for date_id in date_ids:
                try:
                    cal = LocalBodyCalendar.objects.get(pk=date_id)
                    # Check if this date is already booked by this user
                    if not CustomerPickupDate.objects.filter(
                        user=request.user,
                        localbody_calendar=cal
                    ).exists():
                        CustomerPickupDate.objects.create(
                            user=request.user,
                            waste_info=info,
                            localbody_calendar=cal
                        )
                except LocalBodyCalendar.DoesNotExist:
                    messages.error(request, f"Selected pickup date {date_id} is invalid.")
            messages.success(request, f"Successfully booked {len(date_ids)} pickup date(s).")

        return render(request, "waste_success.html", {"info": info})

    return render(request, "waste_form.html", {
        "states": states,
        "ward_range": ward_range,
        "bag_range": bag_range,
        "ward_options": ward_options,
        "selected_dates": [],
        "districts": [],
        "localbodies": [],
        "info": None,
    })


@login_required
@user_passes_test(lambda u: u.role == 0)
def waste_profile_update(request, pk):
    info = get_object_or_404(CustomerWasteInfo, pk=pk, user=request.user)
    states = State.objects.all()
    ward_range = range(1, 75)
    bag_range = range(1, 11)
    ward_options = get_ward_options()

    # Preload districts & localbodies for the selected state/district
    districts = District.objects.filter(state=info.state) if info.state else []
    localbodies = LocalBody.objects.filter(district=info.district) if info.district else []

    # Preload existing selected dates
    selected_dates = CustomerPickupDate.objects.filter(waste_info=info)

    if request.method == "POST":
        # Store old coordinates for comparison
        old_latitude = info.latitude
        old_longitude = info.longitude

        # Get and validate new coordinates
        latitude_raw = request.POST.get("latitude")
        longitude_raw = request.POST.get("longitude")
        new_latitude, new_longitude = validate_coordinates(latitude_raw, longitude_raw)

        # Update main waste info
        info.full_name = request.POST.get("full_name")
        info.secondary_number = request.POST.get("secondary_number")
        info.pickup_address = request.POST.get("pickup_address")
        info.landmark = request.POST.get("landmark")
        info.latitude = new_latitude
        info.longitude = new_longitude
        info.state_id = request.POST.get("state")
        info.district_id = request.POST.get("district")
        info.localbody_id = request.POST.get("localbody")
        info.ward = request.POST.get("ward")
        info.number_of_bags = request.POST.get("number_of_bags")
        info.waste_type = request.POST.get("waste_type")
        info.comments = request.POST.get("comments")
        info.pincode = request.POST.get("pincode")
        info.save()

        # Track location change if coordinates changed
        if new_latitude and new_longitude:
            if old_latitude != new_latitude or old_longitude != new_longitude:
                CustomerLocationHistory.objects.create(
                    waste_info=info,
                    latitude=new_latitude,
                    longitude=new_longitude,
                    changed_by=request.user
                )
                messages.success(request, "Waste profile and location updated successfully!")
            else:
                messages.success(request, "Waste profile updated successfully!")
        else:
            messages.warning(request, "Waste profile updated without location data.")

        # Handle pickup date update (replace old ones with new ones if given)
        selected_date_ids = request.POST.get("selected_date", "")
        if selected_date_ids:
            # Remove old pickup dates for this profile
            CustomerPickupDate.objects.filter(waste_info=info).delete()

            # Process new pickup dates (multiple selection)
            date_ids = [int(id_str) for id_str in selected_date_ids.split(',') if id_str.isdigit()]
            # Limit to 4 bookings
            date_ids = date_ids[:4]

            for date_id in date_ids:
                try:
                    cal = LocalBodyCalendar.objects.get(pk=date_id)
                    # Check if this date is already booked by this user
                    if not CustomerPickupDate.objects.filter(
                        user=request.user,
                        localbody_calendar=cal
                    ).exists():
                        CustomerPickupDate.objects.create(
                            user=request.user,
                            waste_info=info,
                            localbody_calendar=cal
                        )
                except LocalBodyCalendar.DoesNotExist:
                    messages.error(request, f"Selected pickup date {date_id} is invalid.")
            messages.success(request, f"Successfully updated to {len(date_ids)} pickup date(s).")

        return redirect("customer:waste_profile_detail", pk=info.id)

    return render(request, "waste_form.html", {
        "states": states,
        "ward_range": ward_range,
        "bag_range": bag_range,
        "ward_options": ward_options,
        "selected_dates": selected_dates,
        "districts": districts,
        "localbodies": localbodies,
        "info": info,
    })


@login_required
@user_passes_test(is_customer)
def waste_profile_delete(request, pk):
    info = get_object_or_404(CustomerWasteInfo, pk=pk, user=request.user)
    if request.method == "POST":
        info.delete()
        messages.success(request, "Waste profile deleted successfully!")
        return redirect("customer:waste_profile_list")
    return render(request, "waste_profile_delete.html", {"info": info})


@login_required
@user_passes_test(is_customer)
@require_GET
def get_available_dates(request, localbody_id):
    """Get available pickup dates for a local body"""
    # Get all dates for this local body
    all_dates = LocalBodyCalendar.objects.filter(localbody_id=localbody_id)

    # Get dates already booked by this user
    booked_dates = CustomerPickupDate.objects.filter(
        user=request.user,
        localbody_calendar__localbody_id=localbody_id
    ).values_list('localbody_calendar_id', flat=True)

    data = []
    for d in all_dates:
        # Mark as "Picked" if already booked by this user
        picked = d.id in booked_dates
        data.append({
            "id": d.id,
            "date": d.date.isoformat(),
            "title": "Picked" if picked else "Available",
            "picked": picked
        })
    return JsonResponse(data, safe=False)


@login_required
@user_passes_test(is_customer)
@require_GET
def load_districts_customer(request, state_id):
    """Load districts based on selected state"""
    districts = District.objects.filter(state_id=state_id).values('id', 'name')
    return JsonResponse(list(districts), safe=False)


@login_required
@user_passes_test(is_customer)
@require_GET
def load_localbodies_customer(request, district_id):
    """Load local bodies based on selected district"""
    localbodies = LocalBody.objects.filter(district_id=district_id).values('id', 'name', 'body_type')
    return JsonResponse(list(localbodies), safe=False)


@login_required
@user_passes_test(is_customer)
def save_pickup_date(request):
    """Save or update pickup date"""
    if request.method == "POST":
        user = request.user
        date_id = request.POST.get("pickup_date")
        localbody_calendar = get_object_or_404(LocalBodyCalendar, pk=date_id)

        # Create or update
        pickup_date, created = CustomerPickupDate.objects.update_or_create(
            user=user,
            defaults={"localbody_calendar": localbody_calendar}
        )

        if created:
            messages.success(request, "Pickup date saved successfully!")
        else:
            messages.info(request, "Pickup date updated successfully!")

        return JsonResponse({"status": "success", "created": created})

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)


@login_required
@user_passes_test(is_customer)
@require_GET
def validate_location(request):
    """
    API endpoint to validate coordinates from frontend
    Usage: GET /validate-location/?lat=10.5276&lng=76.2144
    """
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')

    lat, lng = validate_coordinates(latitude, longitude)

    if lat and lng:
        return JsonResponse({
            "valid": True,
            "latitude": str(lat),
            "longitude": str(lng),
            "message": "Coordinates are valid"
        })
    else:
        return JsonResponse({
            "valid": False,
            "message": "Invalid coordinates. Latitude must be between -90 and 90, Longitude between -180 and 180."
        }, status=400)


@login_required
@user_passes_test(is_customer)
def location_history(request, pk):
    """
    View location change history for a waste profile
    """
    info = get_object_or_404(CustomerWasteInfo, pk=pk, user=request.user)
    history = CustomerLocationHistory.objects.filter(waste_info=info).order_by('-changed_at')

    return render(request, "location_history.html", {
        "info": info,
        "history": history
    })


@login_required
@user_passes_test(is_customer)
@require_GET
def get_location_by_address(request):
    """
    API endpoint for geocoding - convert address to coordinates
    This would typically call Google Geocoding API from backend
    For now, returns a placeholder response
    """
    address = request.GET.get('address')

    if not address:
        return JsonResponse({"error": "Address parameter is required"}, status=400)

    # TODO: Implement actual Google Geocoding API call here
    # For now, return placeholder
    return JsonResponse({
        "success": False,
        "message": "Geocoding should be done on frontend using Google Maps JavaScript API"
    })


@login_required
@user_passes_test(is_customer)
def export_locations(request):
    """
    Export all customer locations as JSON for mapping/analytics
    """
    profiles = CustomerWasteInfo.objects.filter(
        user=request.user,
        latitude__isnull=False,
        longitude__isnull=False
    ).values(
        'id',
        'full_name',
        'pickup_address',
        'latitude',
        'longitude',
        'waste_type',
        'status',
        'created_at'
    )

    return JsonResponse(list(profiles), safe=False)







