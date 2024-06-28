# Import your blueprint
from app.routes import bp as main_bp

app = Flask(__name__)
csrf = CSRFProtect(app)

# Load configuration based on environment
if "WEBSITE_HOSTNAME" not in os.environ:
    # Local development
    app.config.from_object('config.DevelopmentConfig')
else:
    # Production
    app.config.from_object('config.ProductionConfig')

# Initialize session
Session(app)

# Initialize the database connection
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models after db initialization to avoid circular import issues
from app.models import AirbnbReview, AirbnbRawData

# Register the blueprint
app.register_blueprint(main_bp)

@app.route("/", methods=["GET"])
def index():
    print("Request for index page received")
    return render_template("index.html")

@app.route("/run_cleaning", methods=["POST"])
@csrf.exempt
def run_cleaning():
    try:
        # Your data processing logic here
        flash("Data processing completed successfully!")
    except Exception as e:
        print(f"Error during data processing: {e}")
        flash("An error occurred during data processing.")
    return redirect(url_for('index'))

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
