from flask import g, render_template, request, url_for, Blueprint
from itsdangerous import URLSafeSerializer, BadData
from flask import current_app

from tamflip.api_module import query_tracked_flight
from tamflip.flight_tracker import get_tracked_flights
from tamflip.flight_tracker import update_stored_prices

bp = Blueprint('flightstatus', __name__, url_prefix="/flightstatus")


@bp.route('/<token>', methods=['GET'])
def index(token):
    # Token verification
    with open('credentials.txt') as f:
        credentials = {k: v for k, v in map(str.split, f.readlines())}
        server_secret = credentials['SERVER_SECRET']

    serializer = URLSafeSerializer(server_secret, salt='flightstatus')
    try:
        email = serializer.loads(token)
    except BadData as e:
        return 'Invalid token provided'

    # Get flight details from db and then query the api
    flight_statuses = []
    updates = []
    for flight in get_tracked_flights(current_app, email):
        flight_details, curr_price = query_tracked_flight(flight)

        # If no results are returned by the api
        if curr_price == -1:
            continue

        flight_statuses.append((flight_details,
                                float(flight['prev_price']),
                                float(curr_price)))

        if float(curr_price) != float(flight['prev_price']):
            updates.append((flight['id'], curr_price))

    print(flight_statuses)
    # Update prices in database
    update_stored_prices(current_app, updates)
    return render_template(
        'flight_email.html',
        flight_statuses=flight_statuses
    )
