================================================================================
IntelligentSystem - Season Ticket Renewal Model
================================================================================

OVERVIEW
--------
This project implements the season-ticket renewal model from the ICT 338
Intelligent Systems Week 5 material (ABMS for customer behavior).

It has two parts:

  1. A Flask REST API that computes a renewal rate from five 0-1 inputs and
     stores every scenario in Google Cloud Firestore.
  2. A Streamlit dashboard that explains what each variable means, draws the
     model flow, and lets you run what-if simulations.

The model itself is simple:

  Inputs X1-X5 -> hidden nodes h1/h2 -> hidden nodes h3/h4 -> output O

All variables are measured on a 0-1 scale. All weights and input values are
ASSUMPTIONS, not values taken from the research papers. The papers support the
direction and relative importance of the links only.


PROJECT FILES
-------------
main.py                                  Flask API + Firestore persistence
dashboard.py                             Streamlit dashboard
requirements.txt                         Python dependencies
Renewal_Model_Conceptual_Numerical.xlsx  Model concept, equations, sample values
Variable_Definitions.docx                Plain-language variable definitions
key.json                                 Firebase service account key (NOT in git)
myenv/                                   Local virtual environment (NOT in git)


REQUIREMENTS AND SETUP
----------------------
Python 3.14 was used for this project.

Create and activate the virtual environment, then install the dependencies:

  python3 -m venv myenv
  source myenv/bin/activate
  pip install -r requirements.txt

On this machine the environment already exists:

  myenv/bin/python --version
  myenv/bin/pip install -r requirements.txt


FIREBASE / FIRESTORE SETUP
--------------------------
1. Create a Firebase project and enable Cloud Firestore.
2. Create a service account key (Firebase console -> Project settings ->
   Service accounts -> Generate new private key) and save it as:

     key.json

   in the project root.

   Alternatively, put the key anywhere and point to it with the
   FIREBASE_CREDENTIALS environment variable:

     export FIREBASE_CREDENTIALS=/path/to/key.json

3. The key is already excluded by .gitignore. Never commit or share it.
   Keep its permissions restricted:

     chmod 600 key.json

Firestore layout:

  renewal_rates/{renewal_rateN}
    X1, X2, X3, X4, X5           top-level copies of the inputs
    inputs: {X1..X5}             nested copies of the inputs
    intermediates: {h1..h4, s}   hidden node values
    renewal_rate: number         final O value

  meta/renewal_rate_counter
    value: number                last used numeric scenario id


RUNNING THE PROJECT
-------------------
Start the API (terminal 1):

  cd /home/niehlz/Projects/IntelligentSystem
  myenv/bin/python main.py

  API: http://localhost:5000

Start the dashboard (terminal 2):

  cd /home/niehlz/Projects/IntelligentSystem
  myenv/bin/streamlit run dashboard.py

  Dashboard: http://localhost:8501

The dashboard's "Saved scenarios" tab reads data through the Flask API, so the
API must be running for that tab. To use a different API address:

  export RENEWAL_API_URL=http://your-host:5000


API REFERENCE
-------------
Base URL: http://localhost:5000

  GET    /renewal_rates              List all saved scenarios
  POST   /renewal_rates              Compute and save a new scenario
  GET    /renewal_rates/<id>         Get one scenario
  PUT    /renewal_rates/<id>         Update the renewal_rate value
  DELETE /renewal_rates/<id>         Delete a scenario

POST requires X1, X2, X3, X4 and X5 as floats. Both form-encoded and JSON
bodies are accepted.

Form example:

  curl -X POST http://localhost:5000/renewal_rates \
    -d "X1=0.5" -d "X2=0.7" -d "X3=0.1" -d "X4=0.6" -d "X5=0.8"

JSON example:

  curl -X POST http://localhost:5000/renewal_rates \
    -H "Content-Type: application/json" \
    -d '{"X1": 0.5, "X2": 0.7, "X3": 0.1, "X4": 0.6, "X5": 0.8}'

Example response (HTTP 201):

  {
    "renewal_rate1": {
      "X1": 0.5, "X2": 0.7, "X3": 0.1, "X4": 0.6, "X5": 0.8,
      "inputs": {"X1": 0.5, "X2": 0.7, "X3": 0.1, "X4": 0.6, "X5": 0.8},
      "intermediates": {
        "h1": 0.522, "h2": 0.612,
        "h3": 0.185464, "h4": 0.185464, "s": 0.814536
      },
      "renewal_rate": 0.3721912730009128
    }
  }

Other examples:

  curl http://localhost:5000/renewal_rates
  curl http://localhost:5000/renewal_rates/renewal_rate1
  curl -X PUT http://localhost:5000/renewal_rates/renewal_rate1 \
    -H "Content-Type: application/json" -d '{"renewal_rate": 0.9}'
  curl -X DELETE http://localhost:5000/renewal_rates/renewal_rate1

Status codes:

  200  successful read / update response
  201  scenario created or updated
  204  scenario deleted
  400  missing or non-numeric input
  404  scenario id not found
  415  request body was not readable (fixed; form and JSON both work now)

Notes:

  - IDs are sequential: renewal_rate1, renewal_rate2, ...
    The counter in meta/renewal_rate_counter is updated in a Firestore
    transaction so concurrent POSTs cannot reuse an ID.
  - PUT merges the new renewal_rate into the existing document, so the stored
    inputs and intermediates are preserved.
  - GET /renewal_rates returns a JSON object keyed by scenario id. It returns
    {} when the collection is empty.


MODEL AND VARIABLES
-------------------
Input layer:

  X1  Seat quality        Comfort and view of the holder's seat.
                          0 = poor, 1 = excellent. Raises h1.
  X2  Team performance    Recent on-field success.
                          0 = poor, 1 = excellent. Raises h1 (smaller weight).
  X3  Expensive price     Perceived price burden.
                          0 = cheap, 1 = very expensive. Higher is worse.
                          Lowers both h1 and h2.
  X4  Package benefit     Perks, discounts, exclusive benefits.
                          0 = none, 1 = many. Raises h2.
  X5  Stadium access      Ease of getting to the stadium.
                          0 = hard, 1 = easy. Raises h2.

Hidden layer:

  h1  Satisfaction        Overall evaluation of the season ticket experience.
                          Lower when price is high.
  h2  Switching cost      How locked-in the holder feels after buying. Falls
                          when the renewal price is raised.
  h3  Peer pressure       Outside pressure from peers to leave. Low when h1
                          and h2 are both high.
  h4  Turnover            Tendency to leave (churn). Same logic as h3.

Output:

  O   Renewal rate        Likelihood the holder renews.
                          0 = leaves, 1 = renews.

Equations:

  h1 = (alpha * X2 + (1 - alpha) * X1) * (1 - X3)
  h2 = (alpha2 * X4 + (1 - alpha2) * X5) * (1 - X3)
  h3 = (1 - h1) * (1 - h2)
  h4 = (1 - h1) * (1 - h2)
  aggregated_impact = w3 * (1 - h3) + w4 * (1 - h4)
  O(t+1) = O(t) + eta * (aggregated_impact - O(t)) * dt

The (1 - value) terms flip a negative factor. For example, a high price X3
lowers both h1 and h2.

NOTE: h3 and h4 currently use the same formula, so they always have equal
values. The dashboard displays this limitation as well.


PARAMETER DEFAULTS
------------------
API (main.py):
  alpha  = 0.4    alpha2 = 0.6
  w3     = 0.4    w4     = 0.6
  eta    = 0.03   dt     = 0.02
  O(0)   = 0.1    steps  = 800

Excel / dashboard simulator defaults:
  alpha  = 0.4    alpha2 = 0.6
  w3     = 0.4    w4     = 0.6
  eta    = 0.5    dt     = 1.0
  O(0)   = 0.5    steps  = 20 (adjustable in the dashboard)

The equations are identical, but the timing assumptions differ. This means a
scenario saved through the API can have a different renewal_rate from the same
inputs in the dashboard simulator. The dashboard shows a note about this in the
"Saved scenarios" tab.

With the Excel sample values (X1=0.7, X2=0.6, X3=0.5, X4=0.6, X5=0.5) the
dashboard reproduces the worked example:

  h1 = 0.330
  h2 = 0.280
  h3 = h4 = 0.482
  aggregated impact = 0.518
  O converges to 0.518


DASHBOARD
---------
Run with:

  myenv/bin/streamlit run dashboard.py

Tabs:

  Model overview      Visual flow diagram and all equations.
  Variable dictionary Definitions and effects of X1-X5, h1-h4 and O.
  What-if simulator   Sliders for the inputs and model parameters, live
                      metrics for the hidden nodes, a convergence chart, and
                      a price-sensitivity comparison.
  Saved scenarios     Reads renewal_rates through the Flask API and shows a
                      table plus a renewal-rate bar chart.

The simulator defaults match the Excel worked example. The saved-scenarios tab
needs the API to be running; click "Load saved scenarios" after starting it.


TROUBLESHOOTING
---------------
"Firebase service account key not found at ..."
  Put key.json in the project root, or set FIREBASE_CREDENTIALS to its path.

Permission denied / 403 from Firestore
  Check that Firestore is enabled for the project and that the service account
  has access to it.

Dashboard's Saved scenarios tab cannot reach the API
  Start the Flask API with: myenv/bin/python main.py
  Or set RENEWAL_API_URL to the correct address before starting Streamlit.

POST returns 415
  This was a Flask 3.1 / Flask-RESTful reqparse incompatibility. The API now
  reads request.form or request.get_json() directly, so both form data and
  JSON work. If you still see it, check that you are running the current
  main.py.

Dashboard starts but shows an import error
  Install the dependencies into the same environment:
    myenv/bin/pip install -r requirements.txt


SECURITY NOTES
--------------
- key.json and other credential files are excluded by .gitignore
  (key.json, serviceAccount.json, *credentials*.json, *.pem, *.key, .env).
- Never commit or share the service account key.
- If the key is ever exposed, revoke it in the Firebase console and generate a
  new one.
- The current API has no authentication and binds to 0.0.0.0. Use it only on a
  trusted network, or add authentication before exposing it publicly.

================================================================================
Sources: Renewal_Model_Conceptual_Numerical.xlsx, Variable_Definitions.docx
(ICT 338 Intelligent Systems, Week 5)
================================================================================
