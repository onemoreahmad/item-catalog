#!/usr/bin/env python3

# Import
# ------------------------------------------
from flask_restful import Api, Resource
from flask import Flask, send_from_directory, render_template, request, flash
from flask import redirect, make_response, session, url_for, current_app
from flask_login import LoginManager, logout_user, login_required
from flask_login import login_user, current_user
from authomatic import Authomatic
from flask_orator import Orator
from orator.orm import has_many, belongs_to
from authomatic.adapters import WerkzeugAdapter


# Configure App
# ------------------------------------------
DEBUG = True
ORATOR_DATABASES = {
    'development': {
        'driver': 'sqlite',
        'database': 'database.db'
    }
}

app = Flask(__name__, template_folder='templates', static_url_path='')
app.config.from_object(__name__)
app.secret_key = 'LETSDOIT'
db = Orator(app)


# User Model
# ------------------------------------------
class User(db.Model):
    __table__ = 'users'
    __fillable__ = ['email', 'name']
    __timestamps__ = False

    @has_many
    def items(self):
        return Item

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.get_attribute('id')


# Item Model
# ------------------------------------------
class Item(db.Model):
    __table__ = 'items'
    __fillable__ = ['title', 'image', 'description']
    __hidden__ = ['category_id', 'user_id']
    __timestamps__ = False

    @belongs_to
    def category(self):
        return Category

    @belongs_to
    def user(self):
        return User


# Category Model
# ------------------------------------------
class Category(db.Model):
    __table__ = 'categories'
    __fillable__ = ['title']
    __timestamps__ = False

    @has_many
    def items(self):
        return Item


# Authentication
# ------------------------------------------

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.unauthorized_handler
def unauthorized_access():
    return render_template('401.html'), 401


@login_manager.user_loader
def load_user(user_id):
    return User.find(user_id)


# Social Login
# ------------------------------------------
@app.route('/login/<provider_name>')
def login_with(provider_name):
    response = make_response()

    authomatic = Authomatic({
        'default': 'google',
        'google': {
            'class_': 'authomatic.providers.oauth2.Google',
            'consumer_key': '426158043393-j1gnqba0dpucop2o5m9lo7m248vr1744'
                            '.apps.googleusercontent.com',
            'consumer_secret': 'd88vSFHyhZJ63O4ug6GrksTB',
            'scope': ['profile', 'email'],
            'url': 'https://www.googleapis.com/userinfo/v2/me',
        },
    }, app.secret_key)

    result = authomatic.login(
        WerkzeugAdapter(request, response),
        provider_name, None, session=session,
        session_saver=lambda: app.save_session(session, response)
    )

    if result and result.user and result.user.credentials:
        response = result.provider.access(
            authomatic.config.get(provider_name).get('url')
        )

        if response.status == 200:
            user = User.first_or_new(email=response.data.get('email'))
            user.name = response.data.get('name')
            user.save()
            login_user(user)

        return redirect(url_for('index'))
    return response


# Logout
# ------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# Static Files
# ------------------------------------------
@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory('public/css', filename)


@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory('public/js', filename)


@app.route('/images/<path:filename>')
def images(filename):
    return send_from_directory('public/images', filename)


# Category API
# ------------------------------------------
class CategoryAPI(Resource):
    def get(self):
        return {'categories': Category.with_('items').get().serialize()}

api = Api(app)
api.add_resource(CategoryAPI, '/api/v1/catalog.json')


# Home Page
# ------------------------------------------
@app.route('/')
def index():
    featured_item = Item.with_('category').take(1).order_by('id', 'desc')
    latest_items = Item.with_('category').take(10).order_by('id', 'desc')

    return render_template(
        'index.html', categories=Category.all(),
        latest_items=latest_items.get(),
        featured_item=featured_item.first()
    )


# Category Page
# ------------------------------------------
@app.route('/catalog/<category_id>/')
@app.route('/catalog/<category_id>/items/')
def list_items(category_id):
    category = Category.find(category_id)
    return render_template(
        'category.html', categories=Category.all(), category=category,
        items=category.items
    )


# View Item Page
# ------------------------------------------
@app.route('/catalog/<category_id>/item/<item_id>/')
def view_item(category_id, item_id):
    item = Item.find(item_id)
    return render_template(
        'item_view.html',
        categories=Category.all(),
        category=item.category,
        item=item
    )


# Add Item Page
# ------------------------------------------
@app.route('/catalog/add')
@app.route('/catalog/<category_id>/add')
@login_required
def add_item(category_id=None):
    current_category = Category.find(category_id)
    return render_template(
        'item_add.html',
        categories=Category.all(),
        current_category=current_category
    )


# Post Add Item
# ---------------------------------------------------------------
@app.route('/catalog/store', methods=['POST'])
@login_required
def store_item():
    category = Category.find_or_fail(request.form['category_id'])
    item = Item()

    item.title = request.form['title']
    item.image = request.form['image']
    item.description = request.form['description']
    item.category().associate(category)
    item.user().associate(current_user)
    item.save()

    return redirect(url_for(
        'view_item',
        categories=Category.all(),
        category_id=category.id,
        item_id=item.id
    ))


# Edit Item Page
# ------------------------------------------
@app.route('/catalog/<category_id>/item/<item_id>/edit')
@login_required
def edit_item(category_id, item_id):
    item = Item.find(item_id)

    if not item.user or item.user.id != current_user.id:
        return current_app.login_manager.unauthorized()

    return render_template(
        'item_edit.html', categories=Category.all(), item=item)


# Post Update Item
# ------------------------------------------
@app.route('/catalog/update', methods=['POST'])
@login_required
def update_item():
    category = Category.find_or_fail(request.form['category_id'])
    item = Item.find_or_fail(request.form['item_id'])

    if not item.user or item.user.id != current_user.id:
        return current_app.login_manager.unauthorized()

    item.title = request.form['title']
    item.image = request.form['image']
    item.description = request.form['description']
    item.category().associate(category)
    item.user().associate(current_user)
    item.save()

    return redirect(url_for(
        'view_item',
        categories=Category.all(),
        category_id=category.id,
        item_id=item.id
    ))


# Delete Item
# ------------------------------------------
@app.route('/catalog/destroy', methods=['POST'])
@login_required
def destroy_item():
    item = Item.find_or_fail(request.form['item_id'])

    if not item.user or item.user.id != current_user.id:
        return current_app.login_manager.unauthorized()

    item.delete()
    return redirect(url_for('list_items', category_id=item.category.id))


# Not Found Page
# ------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Run App
# ------------------------------------------
if __name__ == '__main__':
    app.run(host='localhost', port=5000)
