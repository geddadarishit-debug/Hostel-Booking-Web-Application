from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_migrate import Migrate
from collections import defaultdict
app = Flask(__name__)
app.secret_key = "alamatihabibo"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)

with app.app_context():
    # User Model
    db.metadata.clear()
    db.create_all()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), nullable=True)
    hostels = db.relationship('Hostel', back_populates='owner')
    bookings = db.relationship('Booking', back_populates='customer')
    profile_picture=db.Column(db.String(200), nullable=True,default='default_profile_picture_of_account.jfif')    

    def __repr__(self):
        return f"User('{self.username}')"
# Hostel Model
class Hostel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.String(), nullable=False)
    availability = db.Column(db.Boolean, default=True)
    vacancies = db.Column(db.Integer, default=10, nullable=False)  # New field for vacancies
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', back_populates='hostels')
    images = db.Column(db.String(500), nullable=True)
    bookings = db.relationship('Booking', back_populates='hostel', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='hostel', lazy=True)
    description = db.Column(db.Text, nullable=True,default="No description provided")
    phone_number = db.Column(db.String(15), nullable=True)

    @property
    def accepted_bookings(self):
        return Booking.query.filter_by(hostel_id=self.id, status="accepted").count()

    def accept_booking(self, booking):
        if self.vacancies > 0:
            self.vacancies -= 1
            booking.status = "accepted"
        else:
            raise ValueError("Cannot accept booking. No vacancies available!")

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    hostel = db.relationship('Hostel', back_populates='reviews')  # Renamed and paired with reviews
    reviewer_rel = db.relationship('User', backref=db.backref('user_reviews', lazy=True))

    def __repr__(self):
        return f"Review('{self.comment}', '{self.reviewer_rel.username}')"
# Booking Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostel_id = db.Column(db.Integer, db.ForeignKey('hostel.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    customer = db.relationship('User', back_populates='bookings')
    hostel = db.relationship('Hostel', back_populates='bookings')
    accepted_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"Booking('{self.hostel.name}', '{self.customer.username}', '{self.status}')"



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if it's a registration request
        if "rusername" in request.form:
            username = request.form["rusername"]
            password = request.form["rpassword"]
            user_type = request.form["user_type"]
            phone_number = request.form.get("rphone_number")

            # Check if a user with the same username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already taken. Please choose another username.", "error")
                return render_template("login.html")
            
            profile_picture = request.files.get("rprofile_picture")

            if profile_picture:
                print(f"📂 File received: {profile_picture.filename}")  # Debug
            else:
                print("❌ No file received from the form!")  # Debug

            profile_picture_filename = 'default_profile_picture_of_account.jfif'  # Default value
            if profile_picture and profile_picture.filename:
                filename = secure_filename(profile_picture.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                print(f"Attempting to save file to: {file_path}")  # Debug

                try:   
                    profile_picture.save(file_path)
                    print(f"✅ Image saved successfully: {file_path}")  # Debug
                    profile_picture_filename = filename
                except Exception as e:
                    print(f"❌ Error saving image: {e}")  # Catch error


            user = User(username=username,
                        password=password,
                        user_type=user_type,
                        phone_number=phone_number,
                        profile_picture=profile_picture_filename)
            db.session.add(user)
            db.session.commit()
            print(f"📸 Stored profile picture filename in DB: {user.profile_picture}")

            db.session.refresh(user)
            flash("Registered successfully!", "success")
            return redirect(url_for("login"))  # Redirect back to the same page

        # Check if it's a login request
        elif "lusername" in request.form:
            username = request.form["lusername"].strip()
            password = request.form["lpassword"].strip()
            user = User.query.filter_by(username=username, password=password).first()
            print(f"Trying to log in: {username} / {password}")

            if user:
                print("✅ user found:", user)

                login_user(user)
                flash("Logged in successfully!", "success")
                
                if user.user_type == "owner":
                # Get all pending booking requests along with hostel names
                    pending_bookings = (
                    db.session.query(Booking, Hostel.name)
                    .join(Hostel)
                    .filter(Hostel.owner_id == user.id, Booking.status == "pending")
                    .all()
                )

                # Group requests by hostel name
                    hostel_requests = defaultdict(int)
                    for booking, hostel_name in pending_bookings:
                        hostel_requests[hostel_name] += 1  # Count pending requests for each hostel

                # Show flash messages with the count
                    for hostel_name, count in hostel_requests.items():
                        flash(f"{hostel_name} has {count} pending booking request(s)", "warning")
                    
                    return redirect(url_for("dashboard"))

                elif user.user_type == "customer":
                    try:
                        latest_booking = (
                        db.session.query(Booking, Hostel.name, Booking.status)
                        .join(Hostel)
                        .filter(Booking.customer_id == user.id)
                        .order_by(Booking.accepted_date.desc().nullslast(), Booking.created_at.desc())
                        .first()
                            )
                        if latest_booking:
                            booking, hostel_name, status = latest_booking
                            last_status_key = f"last_status_{booking.id}"
                            if session.get(last_status_key) != status:
                                if status == "accepted":
                                    flash(f"Your booking at {hostel_name} has been ACCEPTED ✅", "success")
                                elif status in ["declined", "cancelled"]:
                                    flash(f"Your booking at {hostel_name} has been {status.upper()} ❌", "danger")
                            # Store this status in the session so it doesn't show again
                            session[last_status_key] = status
                        
                    except Exception as e:
                        print(f"⚠️ Error fetching latest booking: {e}")
                    return redirect(url_for("dashboard"))
            else:
                flash("Invalid Credentials!", "error")
                print("❌ login failed: user not found")

    return render_template("login.html")

@app.route('/hostel_accepted_bookings/<int:hostel_id>', methods=['GET', 'POST'])
@login_required
def accepted_bookings(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)

    # Ensure that only the hostel owner can access this page
    if hostel.owner_id != current_user.id:
        flash("You are not authorized to view this page.", "error")
        return redirect(url_for('dashboard'))

    accepted_bookings = Booking.query.filter_by(hostel_id=hostel.id, status='accepted').all()

    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        booking = Booking.query.get(booking_id)

        if booking and booking.hostel_id == hostel.id:
            # Increase the vacancies
            hostel.vacancies += 1

            # Change booking status
            booking.status = 'cancelled'
            
            # Remove customer from accepted bookings
            db.session.commit()
            
            flash("Booking removed successfully.", "success")
            return redirect(url_for('hostel_accepted_bookings', hostel_id=hostel.id))

    return render_template('hostel_accepted_bookings.html', hostel=hostel, accepted_bookings=accepted_bookings)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/rishit')
def rishit():
    return redirect('https://www.linkedin.com/in/geddada-rishit-bb579a338/')

@app.route('/yamuna')
def yamuna():
    return redirect('https://www.linkedin.com/in/yamuna-v-2b4a621b3/')

@app.route('/mahidar')
def mahidar():
    return redirect('https://www.linkedin.com/in/gotham-mahidhar-reddy-2014022b7/')

@app.route('/praneeth')
def praneeth():
    return redirect('https://www.linkedin.com/in/gsmpraneeth/')

@app.route('/reshma')
def reshma():
    return redirect('https://www.linkedin.com/in/reshma-gudla-3b0785324/')

@app.route('/dinesh')
def dinesh():
    return redirect('https://www.linkedin.com/in/dinesh-gujju/')

@app.route("/hostel_accepted_bookings/<int:hostel_id>")
def hostel_accepted_bookings(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    accepted_bookings = Booking.query.filter_by(hostel_id=hostel_id, status="accepted").all()
    return render_template("hostel_accepted_bookings.html", hostel=hostel, accepted_bookings=accepted_bookings)

@app.route("/dashboard")
@login_required
def dashboard():
    search_type = request.args.get('search_type', 'name')  # Default to 'name'
    query = request.args.get('query', '').strip()  # Search term, default to empty

    if current_user.user_type == "owner":
        # Fetch hostels owned by the user
        hostels_query = Hostel.query.filter_by(owner_id=current_user.id)

        # Apply search filters
        if query:
            if search_type == "name":
                hostels_query = hostels_query.filter(Hostel.name.ilike(f"%{query}%"))
            elif search_type == "location":
                hostels_query = hostels_query.filter(Hostel.location.ilike(f"%{query}%"))

        hostels = hostels_query.all()
        return render_template("dashboard.html", hostels=hostels)

    else:  # Customer view
        hostels_query = Hostel.query  # Fetch all hostels

        # Apply search filters
        if query:
            if search_type == "name":
                hostels_query = hostels_query.filter(Hostel.name.ilike(f"%{query}%"))
            elif search_type == "location":
                hostels_query = hostels_query.filter(Hostel.location.ilike(f"%{query}%"))

        hostels = hostels_query.all()

        # Fetch the latest booking for each hostel
        bookings = (
            Booking.query.filter_by(customer_id=current_user.id)
            .order_by(Booking.created_at.desc())  # Get latest bookings
            .all()
        )

        hostels_with_bookings = []
        for hostel in hostels:
            latest_booking = next((b for b in bookings if b.hostel_id == hostel.id), None)
            hostels_with_bookings.append((hostel, latest_booking))

        return render_template("dashboard.html", hostels_with_bookings=hostels_with_bookings)
@app.route("/add_hostel", methods=["GET", "POST"])
@login_required
def add_hostel():
    if current_user.user_type != "owner":
        flash("You are not authorized to add a hostel!", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        price = request.form["price"]
        description = request.form["describe"]
        phone_number = request.form["phone_number"]

        # Convert vacancies to an integer (default: 10 if not provided)
        vacancies = request.form.get("vacancies", "10")  # Default as string
        try:
            vacancies = int(vacancies)  # Convert to integer
        except ValueError:
            vacancies = 10  # Fallback to default if conversion fails

        # Handle image uploads
        image_files = request.files.getlist("images")
        image_paths = []
        for image in image_files:
            if image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                image_paths.append(filename)

        # Convert list of images to a comma-separated string or store as NULL
        images = ",".join(image_paths) if image_paths else None

        # Create new hostel entry
        hostel = Hostel(
            name=name,
            location=location,
            price=price,
            owner_id=current_user.id,
            images=images,  # Store filenames, not paths
            vacancies=vacancies,  # Ensure integer
            description=description,
            phone_number=phone_number
        )

        # Save to database
        db.session.add(hostel)
        db.session.commit()
        flash("Hostel added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_hostel.html")


@app.route("/hostel/<int:hostel_id>/book", methods=["GET", "POST"])
@login_required
def book_hostel(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)

    # Check if the hostel has vacancies
    if hostel.vacancies <= 0:
        flash("No vacancies available for this hostel.", "error")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))

    booking = Booking.query.filter_by(hostel_id=hostel_id, customer_id=current_user.id).first()

    if booking:
        if booking.status == "declined":
            # Allow customer to send a new request
            booking.status = "pending"
            db.session.commit()
        elif booking.status == "accepted":
            flash("You have already booked this hostel!", "error")
            return redirect(url_for("hostel_details", hostel_id=hostel_id))
    
    if request.method == "POST":
        # Handle booking request
        booking = Booking(hostel_id=hostel_id, customer_id=current_user.id, status="pending")
        db.session.add(booking)

         # Notify the owner
        
        db.session.commit()
        flash("Booking request sent successfully!", "success")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))

    return render_template("book_hostel.html", hostel=hostel)

@app.route("/hostel/<int:hostel_id>/manage_bookings", methods=["GET", "POST"])
@login_required
def manage_bookings(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    if current_user.id != hostel.owner_id:
        flash("You are not the owner of this hostel!", "error")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))
    bookings = Booking.query.filter_by(hostel_id=hostel_id).all()
    if request.method == "POST":
        booking_id = request.form["booking_id"]
        action = request.form["action"]
        booking = Booking.query.get(booking_id)
        if action == "accept":
            flash("Booking accepted successfully!", "success")
            booking.status = "accepted"
            
        elif action == "decline":
            flash("Booking declined successfully!", "success")
            booking.status = "declined"
            
        db.session.commit()
        flash("Booking updated successfully!", "success")
        return redirect(url_for("manage_bookings", hostel_id=hostel_id))
    return render_template("manage_bookings.html", hostel=hostel, bookings=bookings)

@app.route("/hostel/<int:hostel_id>/review", methods=["GET", "POST"])
@login_required
def add_review(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    booking = Booking.query.filter_by(hostel_id=hostel_id, customer_id=current_user.id, status="accepted").first()
    if booking is None:
        flash("You have not booked this hostel or your booking has not been accepted!", "error")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))
    review = Review.query.filter_by(hostel_id=hostel_id, reviewer_id=current_user.id).first()
    if request.method == "POST":
        rating = int(request.form["rating"])
        comment = request.form["comment"]
        if review:
            review.rating = rating
            review.comment = comment
            db.session.commit()
            flash("Review updated successfully!", "success")
        else:
            review = Review(hostel_id=hostel_id, reviewer_id=current_user.id, rating=rating, comment=comment)
            db.session.add(review)
            db.session.commit()
            flash("Review added successfully!", "success")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))
    if review:
        return render_template("edit_review.html", hostel=hostel, review=review)
    return render_template("add_review.html", hostel=hostel, booking=booking)

@app.route("/hostel/<int:hostel_id>/review/edit", methods=["GET", "POST"])
@login_required
def edit_review(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    review = Review.query.filter_by(hostel_id=hostel_id, reviewer_id=current_user.id).first()
    if request.method == "POST":
        review.comment = request.form["comment"]
        review.rating = request.form["rating"]
        db.session.commit()
        flash("Review updated successfully!", "success")
        return redirect(url_for("hostel_details", hostel_id=hostel_id))
    flash("No review found to edit!", "error")
    return render_template("edit_review.html", hostel=hostel, review=review)

@app.route("/delete_hostel/<int:hostel_id>", methods=["POST"])
@login_required
def delete_hostel(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    if hostel.owner_id == current_user.id:
        db.session.delete(hostel)
        db.session.commit()
        flash('Hostel deleted successfully!', 'success')
    else:
        flash('You do not have permission to delete this hostel.', 'danger')
    return redirect(url_for('dashboard'))

@app.route("/hostel_bookings/<int:hostel_id>", methods=["GET", "POST"])
@login_required
def hostel_bookings(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)

    # Ensure only the owner can access this route
    if hostel.owner_id != current_user.id:
        flash('You do not have permission to view these bookings.', 'danger')
        return redirect(url_for('dashboard'))

    bookings = Booking.query.filter_by(hostel_id=hostel_id).all()

    # 🚨 Flash message if no vacancies
    if hostel.vacancies <= 0:
        flash("No vacancies available for this hostel.", "error")

    if request.method == "POST":
        booking_id = request.form.get("booking_id")
        status = request.form.get("status")
        booking = Booking.query.get_or_404(booking_id)

        if status == "accepted":
            hostel = Hostel.query.get(booking.hostel_id)  # Re-fetch the latest data

            if hostel.vacancies <= 0:
                flash("Cannot accept booking. No vacancies available!", "danger")
                return redirect(url_for("hostel_bookings", hostel_id=hostel_id))

            hostel.vacancies -= 1
            booking.status = "accepted"
            db.session.commit()
            flash("Booking accepted successfully!", "success")

        elif status == "declined":
            booking.status = "declined"
            db.session.commit()
            flash("Booking has been declined.", "success")

        return redirect(url_for("hostel_bookings", hostel_id=hostel_id))

    return render_template("hostel_bookings.html", hostel=hostel, bookings=bookings)

@app.route("/hostel_details/<int:hostel_id>", methods=["GET", "POST"])
@login_required
def hostel_details(hostel_id):
    hostel = Hostel.query.get_or_404(hostel_id)
    booking = Booking.query.filter_by(hostel_id=hostel_id, customer_id=current_user.id).first()

    # Allow customers to view details, but only owners can delete images
    if request.method == "POST" and current_user.user_type == "owner":
        image_to_delete = request.form.get("image_name")
        if image_to_delete and hostel.images:
            image_list = hostel.images.split(",")
            if image_to_delete in image_list:
                image_list.remove(image_to_delete)
                hostel.images = ",".join(image_list) if image_list else None
                db.session.commit()
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_to_delete))
                flash("Image deleted successfully!", "success")
            

    return render_template('hostel_details.html', hostel=hostel, booking=booking)

@app.route("/delete_image/<int:hostel_id>/<image_name>", methods=["POST"])
@login_required
def delete_image(hostel_id, image_name):
    hostel = Hostel.query.get_or_404(hostel_id)
    
    if hostel.owner_id != current_user.id:
        flash("Unauthorized action!", "error")
        return redirect(url_for("dashboard"))

    if hostel.images:
        image_list = hostel.images.split(",")
        if image_name in image_list:
            image_list.remove(image_name)
            hostel.images = ",".join(image_list) if image_list else None
            db.session.commit()
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], image_name))
            flash("Image deleted successfully!", "success")
    
    return redirect(url_for("hostel_details", hostel_id=hostel_id))

@app.route("/logout")
@login_required
def logout():
    logout_user()  
    flash("Logged out successfully!", "success") 
    return redirect(url_for("index"))

@app.route("/accept_booking/<int:booking_id>", methods=["POST"])
@login_required
def accept_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.hostel.owner_id == current_user.id:
        booking.status = "accepted"
        booking.accepted_date = datetime.now()  # Populate the accepted_date column
        db.session.commit()
        flash("Booking accepted successfully!", "success")
    else:
        flash("You do not have permission to accept this booking.", "error")
    return redirect(url_for("hostel_bookings", hostel_id=booking.hostel_id))
@app.route("/decline_booking/<int:booking_id>", methods=["POST"])
@login_required
def decline_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.hostel.owner_id == current_user.id:
        booking.status = "declined"
        db.session.commit()
        flash("Booking declined successfully!", "success")
    else:
        flash("You do not have permission to decline this booking.", "error")
    return redirect(url_for("hostel_bookings", hostel_id=booking.hostel_id))

# Profile Route
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'delete_picture' in request.form:
            user = current_user
            if user.profile_picture != 'default_profile_picture_of_account.jfif':
                old_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                if os.path.exists(old_pic_path):
                    os.remove(old_pic_path)
                user.profile_picture = 'default_profile_picture_of_account.jfif'
                db.session.commit()
                flash('Profile picture deleted and reset to default!', 'success')
            return redirect(url_for('profile'))

        elif 'delete_account' in request.form:
            user = current_user
            if user.user_type == 'owner':
                for hostel in user.hostels:
                    Review.query.filter_by(hostel_id=hostel.id).delete()
                    Booking.query.filter_by(hostel_id=hostel.id).delete()
                    if hostel.images:
                        for image in hostel.images.split(','):
                            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
                            if os.path.exists(image_path):
                                os.remove(image_path)
                    db.session.delete(hostel)
            Booking.query.filter_by(customer_id=user.id).delete()
            Review.query.filter_by(reviewer_id=user.id).delete()
            if user.profile_picture != 'default_profile_picture_of_account.jfif':
                profile_pic_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                if os.path.exists(profile_pic_path):
                    os.remove(profile_pic_path)
            db.session.delete(user)
            db.session.commit()
            logout_user()
            flash('Your account and all associated data have been deleted.', 'success')
            return redirect(url_for('login'))

        elif 'update' in request.form:
            user = current_user
            user.username = request.form['username']
            user.phone_number = request.form['phone_number']
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    if user.profile_picture != 'default_profile_picture_of_account.jfif':
                        old_pic = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                        if os.path.exists(old_pic):
                            os.remove(old_pic)
                    user.profile_picture = filename
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))

    return render_template('profile.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if current_user.password == current_password:
                if new_password == confirm_password:
                    current_user.password = new_password
                    db.session.commit()
                    flash('Password changed successfully!', 'success')
                    return redirect(url_for('profile'))
                else:
                    flash('Passwords do not match!', 'error')
            else:
                flash('Incorrect current password!', 'error')
        except KeyError as e:
            flash(f"Form submission error: Missing field {e}", 'error')
        # Render the form again on error
        return render_template('change_password.html')

    # For GET request, just render the form
    return render_template('change_password.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port, debug=True)
