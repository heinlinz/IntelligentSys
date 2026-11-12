import os

import numpy as np
from flask import Flask, request
from flask_restful import Api, Resource, abort

import firebase_admin
from firebase_admin import credentials, firestore


app = Flask(__name__)
api = Api(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.environ.get(
    'FIREBASE_CREDENTIALS',
    os.path.join(BASE_DIR, 'key.json'),
)
RENEWAL_RATES_COLLECTION = 'renewal_rates'


def init_firestore():
    """Initialize the Firebase Admin SDK once and return a Firestore client."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise RuntimeError(
            "Firebase service account key not found at {}. Put your JSON key "
            "there, or set FIREBASE_CREDENTIALS to its path.".format(
                CREDENTIALS_PATH
            )
        )

    if not firebase_admin._apps:
        cred = credentials.Certificate(CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)

    return firestore.client()


db = init_firestore()
renewal_rates_ref = db.collection(RENEWAL_RATES_COLLECTION)
counter_ref = db.collection('meta').document('renewal_rate_counter')


def get_renewal_rate(renewal_rate_id):
    snapshot = renewal_rates_ref.document(renewal_rate_id).get()
    return snapshot.to_dict() if snapshot.exists else None


def get_renewal_rate_or_404(renewal_rate_id):
    renewal_rate = get_renewal_rate(renewal_rate_id)
    if renewal_rate is None:
        abort(404, message="Renewal rate {} doesn't exist".format(renewal_rate_id))
    return renewal_rate


@firestore.transactional
def next_renewal_rate_id(transaction):
    """Reserve the next renewal_rateN id atomically."""
    snapshot = counter_ref.get(transaction=transaction)
    last_id = snapshot.to_dict().get('value', 0) if snapshot.exists else 0
    transaction.set(counter_ref, {'value': last_id + 1})
    return 'renewal_rate{}'.format(last_id + 1)


def request_data():
    """Read a JSON or form-encoded request body."""
    if request.is_json:
        return request.get_json()
    return request.form


# RenewalRate
# shows a single renewal rate item and lets you update or delete it
class RenewalRate(Resource):
    def get(self, renewal_rate_id):
        return get_renewal_rate_or_404(renewal_rate_id)

    def delete(self, renewal_rate_id):
        get_renewal_rate_or_404(renewal_rate_id)
        renewal_rates_ref.document(renewal_rate_id).delete()
        return '', 204

    def put(self, renewal_rate_id):
        data = request_data()
        renewal_rate = {'renewal_rate': data.get('renewal_rate')}
        renewal_rates_ref.document(renewal_rate_id).set(renewal_rate)
        return renewal_rate, 201


# RenewalRateList
# shows a list of all renewal rates, and lets you POST to compute a new one
class RenewalRateList(Resource):
    def get(self):
        return {
            doc.id: doc.to_dict()
            for doc in renewal_rates_ref.stream()
        }

    def post(self):
        data = request_data()
        values = {}
        errors = {}

        for name in ['X1', 'X2', 'X3', 'X4', 'X5']:
            raw = data.get(name)
            if raw is None:
                errors[name] = '{} is required'.format(name)
                continue
            try:
                values[name] = float(raw)
            except (TypeError, ValueError):
                errors[name] = '{} must be a float value'.format(name)

        if errors:
            abort(400, message=errors)

        # Generate a new renewal_rate_id
        renewal_rate_id = next_renewal_rate_id(db.transaction())

        # Model parameters
        dt = 0.02
        n_steps = 800
        eta = 0.03
        alpha = 0.4
        alpha2 = 0.6
        w3 = 0.4
        w4 = 0.6

        X1, X2, X3, X4, X5 = (
            values['X1'],
            values['X2'],
            values['X3'],
            values['X4'],
            values['X5']
        )

        # Inputs are constant over time, so h and s are constant too
        h1 = (alpha * X2 + (1 - alpha) * X1) * (1 - X3)
        h2 = (alpha2 * X4 + (1 - alpha2) * X5) * (1 - X3)
        h3 = (1 - h1) * (1 - h2)
        h4 = (1 - h1) * (1 - h2)
        s = w3 * (1 - h3) + w4 * (1 - h4)

        # Renewal rate over time
        O = np.zeros(n_steps)
        O[0] = 0.1

        for t in range(1, n_steps):
            O[t] = O[t-1] + eta * (s - O[t-1]) * dt

        # Build the full result: inputs, intermediate values, and final rate
        result = {
            'inputs': {
                'X1': X1,
                'X2': X2,
                'X3': X3,
                'X4': X4,
                'X5': X5
            },
            'intermediates': {
                'h1': float(h1),
                'h2': float(h2),
                'h3': float(h3),
                'h4': float(h4),
                's': float(s)
            },
            'renewal_rate': float(O[-1])
        }

        # Persist it so GET /renewal_rates/<id> returns the same data
        renewal_rates_ref.document(renewal_rate_id).set(result)

        # Return the new renewal rate with its inputs
        return {renewal_rate_id: result}, 201


api.add_resource(RenewalRateList, '/renewal_rates')
api.add_resource(RenewalRate, '/renewal_rates/<renewal_rate_id>')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
