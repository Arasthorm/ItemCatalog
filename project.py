from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, CatalogItem,User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog app"
auth = 0

# Connect to Database and create database session
engine = create_engine('sqlite:///catalogItemWithUsers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/catalog/login')
def login():
    if 'username' in login_session:
        return redirect(url_for('showCategories'))

    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html',STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token

    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    print stored_credentials
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'


    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    flash('You are now logged in as %s' % (login_session['username']))
    output = 'Done!'

    return output


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print result['status']
    if result['status'] != '200':
        print "No result?"
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        login_session.clear()
        flash('You have successfully logged out')
        return redirect(url_for('showCategories'))


@app.route('/catalog/<int:category_id>/item/JSON')
def categoriesItemsJSON(category_id):
    category = session.query(Catalog).filter_by(id=category_id).one()
    items = session.query(CatalogItem).filter_by(
        catalog_id=category_id).all()
    return jsonify(CatalogItems=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/item/<int:item_id>/JSON')
def itemsJSON(category_id, item_id):
    Category_Item = session.query(CatalogItem).filter_by(id=item_id).one()
    return jsonify(Category_Item=Category_Item.serialize)


@app.route('/catalog/JSON')
def categoriesJSON():
    categories = session.query(Catalog).all()
    return jsonify(categories=[c.serialize for c in categories])


# Show all categories
@app.route('/')
@app.route('/catalog/')
def showCategories():

    users = []
    username = ""
    picture = ""
    categories = session.query(Catalog).all()

    for cat in categories:
        users.append(getUserInfo(cat.user_id))

    if 'username' in login_session:
        username = login_session['username']
        picture = login_session['picture']

    return render_template('showCategories.html', categories=categories,
        users=users,username=username,picture=picture,n=len(users))

@app.route('/catalog/new/',methods=['GET', 'POST'])
def newCategory():
    username = ""
    picture = ""
    if request.method == 'POST':
        if request.form['name'] and 'username' in login_session:
            newCategory = Catalog(name=request.form['name'],user_id=login_session['user_id'])
            session.add(newCategory)
            session.commit()
            flash('New Category %s Successfully Created' % (newCategory.name))
        return redirect(url_for('showCategories'))
    else:
        if 'username' in login_session:
            username = login_session['username']
            picture = login_session['picture']
            return render_template('insertCategory.html',username=username,picture=picture);
        return redirect(url_for('showCategories'))

@app.route('/catalog/<int:catalog_id>/edit/', methods=['GET','POST'])
def editCategory(catalog_id):
    username = ""
    picture = ""
    categoryToEdit = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        if 'username' in login_session:
            if login_session['user_id'] == categoryToEdit.user_id:
                if request.form['name']:
                    categoryToEdit.name = request.form['name']
                    session.add(categoryToEdit)
                    session.commit()
                    flash('Category %s Successfully Edited' % (categoryToEdit.name))
        return redirect(url_for('showCategories'))
    else:
        if 'username' in login_session and login_session['user_id'] == categoryToEdit.user_id:
            username = login_session['username']
            picture = login_session['picture']
            return render_template('editCategory.html',category=categoryToEdit,username=username,picture=picture)
        return redirect(url_for('showCategories'))



@app.route('/catalog/<int:catalog_id>/delete/', methods=['GET','POST'])
def deleteCategory(catalog_id):
    username = ""
    picture = ""
    categoryToDelete = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        if login_session['user_id'] == categoryToDelete.user_id:
            session.delete(categoryToDelete)
            session.commit()
            flash('Category %s Successfully Deleted' % (categoryToDelete.name))
        return redirect(url_for('showCategories'))
    else:
        if 'username' in login_session and login_session['user_id'] == categoryToDelete.user_id:
            username = login_session['username']
            picture = login_session['picture']
            return render_template("deleteCategory.html",category=categoryToDelete,username=username,picture=picture)
        return redirect(url_for('showCategories'))


@app.route('/catalog/<int:catalog_id>/', methods=['GET','POST'])
def showItems(catalog_id):
    username = ""
    picture = ""
    category = session.query(Catalog).filter_by(id=catalog_id).one()
    items = session.query(CatalogItem).filter_by(catalog_id=catalog_id).all()

    if 'username' in login_session:
        username = login_session['username']
        picture = login_session['picture']
    return render_template("showItems.html",items=items,category=category,n=len(items),username=username,picture=picture)


@app.route('/catalog/<int:catalog_id>/item/new/', methods=['GET','POST'])
def newItem(catalog_id):
    username = ""
    picture = ""
    category = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        if 'username' in login_session:
            if request.form['name']:
                newItem = CatalogItem(name=request.form['name'],
                                description=request.form['description'],
                                catalog_id = catalog_id,
                                user_id=login_session['user_id'])
                session.add(newItem)
                session.commit()
                flash('Item %s Successfully created' % (newItem.name))
        return redirect(url_for('showItems',catalog_id=catalog_id))
    else:
        if 'username' in login_session:
            username = login_session['username']
            picture = login_session['picture']
            return render_template("insertItem.html",category=category,username=username,picture=picture)
        return redirect(url_for('showItems',catalog_id=catalog_id))

@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/edit', methods=['GET','POST'])
def editItem(catalog_id,item_id):
    username = ""
    picture = ""
    category = session.query(Catalog).filter_by(id=catalog_id).one()
    itemToEdit = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        if login_session['user_id'] == itemToEdit.user_id:
            if request.form['description']:
                itemToEdit.description = request.form['description']
            if request.form['name']:
                itemToEdit.name = request.form['name']
                session.add(itemToEdit)
                session.commit()
                flash('Item %s Successfully editted' % (itemToEdit.name))
        return redirect(url_for('showItems',catalog_id=catalog_id))
    else:
        if 'username' in login_session and login_session['user_id'] == itemToEdit.user_id:
            username = login_session['username']
            picture = login_session['picture']
            return render_template('editItem.html',item=itemToEdit,category=category,username=username,picture=picture)
        return redirect(url_for('showItems',catalog_id=catalog_id))


@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/delete', methods=['GET','POST'])
def deleteItem(catalog_id,item_id):
    username = ""
    picture = ""
    category = session.query(Catalog).filter_by(id=catalog_id).one()
    itemToDelete = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        if login_session['user_id'] == itemToDelete.user_id:
            session.delete(itemToDelete)
            session.commit()
            flash('Item %s Successfully Deleted' % (itemToDelete.name))
        return redirect(url_for('showItems',catalog_id=catalog_id))
    else:
        if 'username' in login_session and login_session['user_id'] == itemToDelete.user_id:
            username = login_session['username']
            picture = login_session['picture']
            return render_template('deleteItem.html',item=itemToDelete,category=category,username=username,picture=picture)
        return redirect(url_for('showItems',catalog_id=catalog_id))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)






