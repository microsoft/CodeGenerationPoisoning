from flask import g, render_template, request, url_for, Blueprint
from itsdangerous import URLSafeSerializer, BadData
from tamflip.db import get_db

bp = Blueprint('unsubscribe', __name__, url_prefix="/unsubscribe")


@bp.route('/<token>', methods=['GET', 'POST'])
def index(token):

    # Token verification
    with open('credentials.txt') as f:
        credentials = {k: v for k, v in map(str.split, f.readlines())}
        server_secret = credentials['SERVER_SECRET']

    serializer = URLSafeSerializer(server_secret, salt='unsubscribe')
    try:
        email = serializer.loads(token)
    except BadData as e:
        return 'Invalid token provided'

    # Take user input, unsubscribe and display confirmation
    if request.method == 'POST':
        # for i in request.form.items():
        #     print(i)

        flightids_continue_tracking = [
            k for (k, v) in request.form.items()
            if v == 'on'
        ]

        # Print rows which will be deleted.
        db = get_db()
        cursor = db.execute(
            """
            SELECT *
            FROM tracked_flights
            WHERE
                email = ?
            AND
                id NOT IN %s
            """ % ('(' + ', '.join(flightids_continue_tracking) + ')'),
            (email,)
        )

        print('Deleting the following rows...')
        for row in cursor.fetchall():
            print(tuple(row))

        # Delete the rows
        db.execute(
            """
            DELETE
            FROM tracked_flights
            WHERE
                email = ?
            AND
                id NOT IN %s
            """ % ('(' + ', '.join(flightids_continue_tracking) + ')'),
            (email,)
        )
        db.commit()

    # Display unsubscribe page
    # Get tracked flights
    db = get_db()
    cursor = db.execute(
        """
        SELECT *
        FROM tracked_flights
        WHERE email = ?
        """,
        (email,)
    )
    column_names = list(map(lambda x: x[0], cursor.description))
    flight_details = [
        {k: v for k, v in zip(column_names, tuple(row))}
        for row in cursor.fetchall()
    ]

    return render_template(
        'unsubscribe.html',
        flight_details=flight_details
    )
