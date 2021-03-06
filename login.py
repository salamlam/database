import bottle
from bottle import route, template, debug, request, redirect
import bottle_session
import MySQLdb
import hashlib
import re

# My implement
from db import *

# Reusable function
def is_signin(session):
    is_signin = session.get('is_signin')
    if is_signin in [True, "True"]:
        return True
    else:
        return False

def check_is_admin(session):
    is_admin = session.get('is_admin')
    if is_admin in [True, "True", 1, "1"]:
        return True
    else:
        return False

def is_user(user_id):
    db = db_login()
    cursor = db.cursor()
    cursor.execute("select * from `user` where `id` = %s", (user_id))
    data = cursor.fetchall()
    if data == ():
        return False
    else:
        return True

def in_airport(place):
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select id from `airport` where location = %s', (place))
    data = cursor.fetchone()
    db.close()
    if data in [(), None]:
        return False, data
    else:
        return True, data[0]
    

# Homework2 pages
@route('/flight/signin')
def server_static_signin(session):
    if is_signin(session):
        redirect('/database/flight/timetable')
    else:
        return template('signin', title="Sign In For Flight Time Table", warning="")

@route('/flight/signin', method='POST')
def do_signin(session):
    user_email = request.forms.get('email')
    passwd = request.forms.get('passwd')
    passwd = hashlib.sha224(passwd).hexdigest()
    return check_signin(user_email, passwd, session)

def check_signin(user_email, passwd, session):
    db = db_login()
    cursor = db.cursor()
    cursor.execute("select `password` from `user` where `account`= %s", (user_email)) 
    data = cursor.fetchall()
    cursor.execute("select `id` from `user` where `account`= %s", (user_email)) 
    user_id = cursor.fetchall()
    db.close()

    if data == ():
        return template('signin', title="Sign In For Flight Time Table", 
                warning="No such user")
    else:
        session['user_id'] = user_id[0][0]
        correct_passwd = data[0][0]
        if correct_passwd != None and passwd == correct_passwd:
            db = db_login()
            cursor = db.cursor()
            cursor.execute("select `is_admin` from `user` where `account`= %s", (user_email)) 
            is_admin = (cursor.fetchall())[0][0]
            db.close()

            session['is_admin'] = is_admin
            session['is_signin'] = True
            redirect('/database/flight/timetable')
        else:
            return template('signin', title="Sign In For Flight Time Table", 
                    warning="Wrong password")

@route('/flight/signup')
def server_static_signup(session):
    session['is_admin'] = False
    session['title'] = "Sign up"
    session['action'] = "signup"
    return template('signup', title="Sign up", warning="",
            is_admin=False, action="signup")

@route('/flight/signup', method = 'POST')
def do_signup(session):
    user_email = request.forms.get('email')
    passwd = request.forms.get('password')
    passwd_conf = request.forms.get('password_confirm')

    title = session.get('title')
    action = session.get('action')

    is_admin = check_is_admin(session)

    if user_email == "":
        return template('signup', title = title, is_admin = is_admin,
                warning = "Email cannot be empty.", action = action)
    elif ' ' in user_email:
        return template('signup', title = title, is_admin = is_admin,
                warning = "Email cannot contain whitespace.", action = action)
    elif passwd == "":
        return template('signup', title = title, is_admin = is_admin,
                warning = "Password cannot be empty.", action = action)
    elif passwd != passwd_conf:
        return template('signup', title = title, is_admin = is_admin,
                warning = "Password Confirmation Failed.", action = action)

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `user` where `account` = %s', (user_email))

    if cursor.fetchall() != ():
        db.close()
        return template('signup', title = title, is_admin = is_admin, 
                warning = "Email is repeate.", action = action)
    else:
        if is_admin == False:
            is_admin = False
            passwd = hashlib.sha224(passwd).hexdigest()
            cursor.execute('insert into `user` values(0, %s, %s, %s)', (user_email, passwd, is_admin))
            db.commit()
            db.close()
            session['is_admin'] = is_admin
            session['is_signin'] = False
            redirect('/database/flight/signin')
        else:
            is_admin = request.forms.get('is_admin')
            if is_admin == 'on':
                is_admin = True
            else:
                is_admin = False

            passwd = hashlib.sha224(passwd).hexdigest()
            cursor.execute('insert into `user` values(0, %s, %s, %s)', (user_email, passwd, is_admin))
            db.commit()
            db.close()

            is_admin = True
            return template('signup', title = title, is_admin = is_admin, 
                    warning = "Sucessfully add user.", action = action)
            

@route('/flight/signout')
def signout(session):
    session['is_signin'] = False
    redirect('/database/flight/signin')

@route('/flight/timetable')
def index(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")
    
    session['url'] ="/database/flight/timetable"
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select f.id, f.flight_number, dep.location, des.location,\
            f.departure_date, f.arrival_date, f.price\
            from `flight` f\
                inner join `airport` as dep\
                    on f.departure = dep.id\
                join `airport` as des\
                    on f.destination = des.id')
    data = cursor.fetchall()
    db.close()

    is_admin = check_is_admin(session)
    return template('timetable', title="Time table for flight", warning="", 
            is_admin = is_admin, data = data, user_id = user_id)

@route('/flight/timetable', method = 'POST')
def timetable_request(session):

    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    is_admin = check_is_admin(session)

    db_col = {'ID':'id', 'Code':'flight_number', 'From':'departure',
        'To':'destination', 'Depart':'departure_date', 'Arrive':'arrival_date',
        'Price':'price'}

    column = request.forms.get('col')
    pattern = request.forms.get('pattern')
    redirect('/database/flight/search/%s/%s' %(column, pattern))

@route('/flight/favorite/<flight_id>')
def add_favorite(session, flight_id):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")
    
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `favorite` where user_id = %s and flight_id = %s', (user_id, flight_id))
    data = cursor.fetchall()
    if data == ():
        cursor.execute('insert into `favorite` values(%s, %s)', (user_id, flight_id))
        db.commit()
        db.close()

    url = session.get('url')
    redirect(url)

@route('/flight/favorite')
def favorite(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    is_admin = check_is_admin(session)

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select flight_id from `favorite` where user_id = %s', (user_id))
    favorite = cursor.fetchall()
    data = []
    
    for flight_id in favorite:
        cursor.execute('select f.id, f.flight_number, dep.location, des.location,\
                f.departure_date, f.arrival_date, f.price\
                from `flight` f\
                    inner join `airport` as dep\
                        on f.departure = dep.id\
                    join `airport` as des\
                        on f.destination = des.id\
                where f.id = %s', (flight_id))
        data.append(cursor.fetchall()[0])

    db.close()

    return template('favorite', title="Comparison sheet", warning="",
            is_admin = is_admin, data = data, user_id = user_id)

@route('/flight/delfavorite/<flight_id>')
def del_favorite(session, flight_id):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    db = db_login()
    cursor = db.cursor()
    cursor.execute('delete from `favorite` where user_id = %s and flight_id = %s', (user_id, flight_id))
    db.commit()
    db.close()

    redirect('/database/flight/favorite')
    
@route('/flight/search/<col>/<pattern>')
def do_search(session, col, pattern):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    is_admin = check_is_admin(session)

    db = db_login()
    cursor = db.cursor()
    pattern = '%' + pattern + '%'
    
    if col == "Code":
        col = "flight_number"
    elif col == "From":
        col = "departure"
    else:
        col = "destination"

    cursor.execute("select f.id, f.flight_number, dep.location, des.location,\
            f.departure_date, f.arrival_date, f.price\
            from `flight` f\
                inner join `airport` as dep\
                    on f.departure = dep.id\
                join `airport` as des\
                    on f.destination = des.id\
             where %s like '%s'" %(col, pattern))

    data = cursor.fetchall()
    db.close()

    session['url'] ="/database/flight/search/" + col + "/" + pattern
    return template('search', title="Search flight", warning="", 
            col = col, pattern = pattern,
            is_admin = is_admin, data = data)
    
@route('/flight/edit/<flight_id>')
def edit(session, flight_id):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    is_admin = check_is_admin(session)

    if is_admin == False:
        redirect('/database/flight/timetable')
    else:
        db = db_login()
        cursor = db.cursor()
        cursor.execute('select f.id, f.flight_number, dep.location, des.location,\
                f.departure_date, f.arrival_date, f.price\
                from `flight` f\
                    inner join `airport` as dep\
                        on f.departure = dep.id\
                    join `airport` as des\
                        on f.destination = des.id\
                where f.id = %s', (flight_id))
        data = (cursor.fetchall())[0]
        db.close()
        return template('edit', title="Edit flight", warning="",
                is_admin = is_admin, data = data, flight_id = flight_id)

@route('/flight/edit/<flight_id>', method='POST')
def do_edit(session, flight_id):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select f.id, f.flight_number, dep.location, des.location,\
            f.departure_date, f.arrival_date, f.price\
            from `flight` f\
                inner join `airport` as dep\
                    on f.departure = dep.id\
                join `airport` as des\
                    on f.destination = des.id\
            where f.id = %s', (flight_id))
    data = (cursor.fetchall())[0]
    db.close()

    flight_number = request.forms.get('code')

    if flight_number == "":
        return template('edit', title="Edit Flight", warning="Code cannot be empty.",
                flight_id = flight_id, data = data)
    if ' ' in flight_number:
        return template('edit', title="Edit Flight", warning="Code cannot contain whitespace.", 
                flight_id = flight_id, data = data)

    depart = request.forms.get('from')

    if depart == "":
        return template('edit', title="Edit Flight", warning="From cannot be empty.", 
                flight_id = flight_id, data = data)
    if ' ' in depart:
        return template('edit', title="Edit Flight", warning="From cannot contain whitespace.", 
                flight_id = flight_id, data = data)

    test, depart_id = in_airport(depart)

    if test == False:
        return template('edit', title="Edit Flight", warning="Don't have this depart in airport", 
                flight_id = flight_id, data = data)

    destination = request.forms.get('to')

    if destination == "":
        return template('edit', title="Edit Flight", warning="To cannot be empty.", 
                flight_id = flight_id, data = data)
    if ' ' in destination:
        return template('edit', title="Edit Flight", warning="To cannot contain whitespace.", 
                flight_id = flight_id, data = data)

    test, dest_id = in_airport(destination)
    if test == False:
        return template('edit', title="Edit Flight", warning="Don't have this destination in airport", 
                flight_id = flight_id, data = data)

    depart_date = request.forms.get('depart_date')

    if depart_date == "":
        return template('edit', title="Edit Flight", warning="Depart cannot be empty.", 
                flight_id = flight_id, data = data)

    arrive_date = request.forms.get('arrive_date')

    if depart_date == "":
        return template('edit', title="Edit Flight", warning="Arrive cannot be empty.",
                flight_id = flight_id, data = data)

    price = request.forms.get('price')

    if price == "":
        return template('edit', title="Edit Flight", warning="Price cannot be empty.",
                flight_id = flight_id, data = data)

    if unicode(price).isnumeric() == False:
        return template('edit', title="Edit Flight", warning="Price should be a number.",
                flight_id = flight_id, data = data)
        
    db = db_login()
    cursor = db.cursor()
    cursor.execute('update `flight` set flight_number = %s where id = %s', (flight_number, flight_id))
    cursor.execute('update `flight` set departure = %s where id = %s', (depart_id, flight_id))
    cursor.execute('update `flight` set destination = %s where id = %s', (dest_id, flight_id))
    cursor.execute('update `flight` set departure_date = %s where id = %s', (depart_date, flight_id))
    cursor.execute('update `flight` set arrival_date = %s where id = %s', (arrive_date, flight_id))
    cursor.execute('update `flight` set price = %s where id = %s', (price, flight_id))

    db.commit()
    db.close()
    redirect('/database/flight/timetable')

@route('/flight/delete/<flight_id>')
def delete(session, flight_id):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')
    else:
        db = db_login()
        cursor = db.cursor()
        cursor.execute('delete from `flight` where id = %s', flight_id)
        db.commit()
        db.close()
        redirect('/database/flight/timetable')

@route('/flight/plane')
def new_plane(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if check_is_admin(session) == True:
        return template('plane', title="New Plane", warning="")
    else:
        redirect('/database/flight/timetable')

@route('/flight/plane', method = 'POST')
def new_plane(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")


    flight_number = request.forms.get('code')

    if flight_number == "":
        return template('plane', title="New Plane", warning="Code cannot be empty.")
    if ' ' in flight_number:
        return template('plane', title="New Plane", warning="Code cannot contain whitespace.")

    depart = request.forms.get('from')

    if depart == "":
        return template('plane', title="New Plane", warning="From cannot be empty.")
    if ' ' in depart:
        return template('plane', title="New Plane", warning="From cannot contain whitespace.")

    test, depart_id = in_airport(depart)
    if test == False:
        return template('plane', title="New Plane", warning="Don't have this depart in airport")

    destination = request.forms.get('to')

    if destination == "":
        return template('plane', title="New Plane", warning="To cannot be empty.")
    if ' ' in destination:
        return template('plane', title="New Plane", warning="To cannot contain whitespace.")

    test, dest_id = in_airport(destination)
    if test == False:
        return template('plane', title="New Plane", warning="Don't have this destination in airport")

    depart_date = request.forms.get('depart_date')
    depart_time = request.forms.get('depart_time')
    departure_date = depart_date + " " + depart_time + ":00"

    if depart_date == "" or depart_time == "":
        return template('plane', title="New Plane", warning="Depart cannot be empty.")

    arrive_date = request.forms.get('arrive_date')
    arrive_time = request.forms.get('arrive_time')
    arrival_date = arrive_date + " " + arrive_time + ":00"

    if depart_date == "" or depart_time == "":
        return template('plane', title="New Plane", warning="Arrive cannot be empty.")

    price = request.forms.get('price')
    
    if price == "":
        return template('plane', title="New Plane", warning="Price cannot be empty.")
        
    db = db_login()
    cursor = db.cursor()
    cursor.execute('insert into `flight` values(0, %s, %s, %s, %s, %s, %s)',
            (flight_number, depart_id, dest_id, departure_date, arrival_date, price))
    db.commit()
    db.close()

    return template('plane', title="New Plane", warning="Sucessfully add.")

# Homework 3 pages
@route('/flight/user')
def manage_user(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')
    
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `user`')
    data = cursor.fetchall()
    db.close()
    return template('user', title="Manage Users", warning="",
            data = data)

@route('/flight/adduser')
def add_user(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/signin')
    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')
    return template('signup', title="Add user", warning="",
            is_admin=True, action="adduser")

@route('/flight/adduser', method = 'POST')
def add_user(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/signin')
    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    session['is_admin'] = True
    session['title'] = "Add user"
    session['action'] = "adduser"
    return do_signup(session)

@route('/flight/deluser/<user_id>')
def del_user(session, user_id):
    my_user_id = session.get('user_id')
    if is_user(my_user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/signin')

    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('delete from `user` where id = %s', (user_id))
    db.commit()
    db.close()

    redirect('/database/flight/user')

@route('/flight/edituser/<user_id>')
def edit_user(session, user_id):
    my_user_id = session.get('user_id')
    if is_user(my_user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    is_admin = check_is_admin(session)
    if is_admin == False:
        redirect('/database/flight/timetable')
    elif is_user(user_id) == False:
        return template('sorry', title="Error", warning="No such user.")
    else:
        db = db_login()
        cursor = db.cursor()
        cursor.execute('select * from `user` where id = %s', (user_id))
        data = (cursor.fetchall())[0]
        db.close()
        return template('edituser', title="Edit User", warning="",
                is_admin = is_admin, data = data, user_id = user_id)

@route('/flight/edituser/<user_id>', method='POST')
def edit_user(session, user_id):
    my_user_id = session.get('user_id')
    if is_user(my_user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `user` where id = %s', (user_id))
    data = (cursor.fetchall())[0]
    db.close()

    is_admin = request.forms.get('is_admin')
    if is_admin == 'on':
        is_admin = True
    else:
        is_admin = False

    db = db_login()
    cursor = db.cursor()
    cursor.execute('update `user` set is_admin = %s where id = %s', (is_admin, user_id))
    db.commit()
    db.close()

    redirect('/database/flight/user')

@route('/flight/airport')
def airport(session):
    if is_signin(session) == False:
        redirect('/database/flight/signin')

    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select a.id, a.name, a.location, a.longitude, a.latitude, c.abbre, a.timezone\
                    from `airport` a\
                        inner join `country` as c\
                            on c.id = a.country_id')
    data = cursor.fetchall()
    db.close()
    return template('airport', title="Airport Management", warning = "",
            data = data)

@route('/flight/addairport')
def add_airport(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/signin')

    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    return template('addairport', title="New Airport", warning="")

@route('/flight/addairport', method = 'POST')
def do_add_airport(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    name = request.forms.get('name')
    location = request.forms.get('location')
    longitude = request.forms.get('longitude')
    latitude = request.forms.get('latitude')
    country = request.forms.get('country')
    timezone = request.forms.get('timezone')

    if name == "":
        return template('addairport', title="New Airport", warning="Name cannot be empty")

    if location == "":
        return template('addairport', title="New Airport", warning="Location cannot be empty")

    if longitude == "":
        return template('addairport', title="New Airport", warning="longitude cannot be empty")

    if float(longitude) > 180 or float(longitude) < -180:
        return template('addairport', title="New Airport", warning="-180 <= longitude <= 180")

    if latitude == "":
        return template('addairport', title="New Airport", warning="latitude cannot be empty")
        
    if float(latitude) > 90 or float(latitude) < -90:
        return template('addairport', title="New Airport", warning="-90 <= latitude <= 90")

    if len(timezone) != 6 or re.match("[-+][0-9]{2}[:][0]{2}", timezone) == None:
        return template('addairport', title="New Airport", warning="timezone format wrong (ex: +08:00)")
    
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select id from `country` where abbre = %s', (country))
    country_id = cursor.fetchone()

    if country_id != None:
        cursor.execute('insert into `airport` values(0, %s, %s, %s, %s, %s, %s)', \
                        (name, location, longitude, latitude, country_id[0], timezone))
        db.commit()
        db.close()
        return template('addairport', title="New Airport", warning="Sucessfully add")
    else:
        db.close()
        return template('addairport', title="New Airport", warning="No such country")

@route('/flight/delairport/<airport_id>')
def del_airport(session, airport_id):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/timetable')

    if check_is_admin(session) == False:
        redirect('database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('delete from `airport` where id = %s', (airport_id))
    db.commit()
    db.close()
    redirect('/database/flight/airport')

@route('/flight/editairport/<airport_id>')
def edit_airport(session, airport_id):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/signin')
        
    if check_is_admin(session) == False:
        redirect('/database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select a.id, a.name, a.location, a.longitude, a.latitude, c.abbre, a.timezone\
                    from `airport` a\
                        inner join `country` as c\
                            on c.id = a.country_id\
                    where a.id = %s', (airport_id))
    data = (cursor.fetchall())[0]
    db.close()
    return template('editairport', title="Edit Airport", warning="",
            data = data, airport_id = airport_id)

@route('/flight/editairport/<airport_id>', method = 'POST')
def do_edit_airport(session, airport_id):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    name = request.forms.get('name')
    location = request.forms.get('location')
    longitude = request.forms.get('longitude')
    latitude = request.forms.get('latitude')
    country = request.forms.get('country')
    timezone = request.forms.get('timezone')

    data = [airport_id, name, location, longitude, latitude, country, timezone]

    if name == "":
        return template('editairport', title="Edit Airport", warning="Name cannot be empty",
               data = data, airport_id = airport_id) 

    if longitude == "":
        return template('editairport', title="Edit Airport", warning="Longitude cannot be empty",
               data = data, airport_id = airport_id) 

    if float(longitude) > 180 or float(longitude) < -180:
        return template('editairport', title="Edit Airport", warning="-180 <= longitude <= 180",
            data = data, airport_id = airport_id)
        
    if latitude == "":
        return template('editairport', title="Edit Airport", warning="Latitude cannot be empty",
               data = data, airport_id = airport_id) 
        
    if float(latitude) > 90 or float(latitude) < -90:
        return template('editairport', title="Edit Airport", warning="-90 <= latitude <= 90",
            data = data, airport_id = airport_id)
    
    if len(timezone) != 6 or re.match("[-+][0-9]{2}[:][0]{2}", timezone) == None:
        return template('editairport', title="New Airport", warning="timezone format wrong (ex: +08:00)")

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select id from `country` where abbre = %s', (country))
    country_id = cursor.fetchone()

    if country_id != None:
        cursor.execute('update `airport` set name = %s,location = %s,\
                                         longitude = %s, latitude = %s,\
                                         country_id = %s, timezone = %s\
                                         where id = %s',\
                                         (name, location, longitude, latitude,\
                                          country_id[0], timezone, airport_id))
        db.commit()
        db.close()
        redirect('/database/flight/airport')
    else:
        db.close()
        return template('editairport', title="Edit Airport", warning="No such country",
            data = data, airport_id = airport_id)

# Homework4
@route('/flight/country')
def country(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/timetable')

    if check_is_admin(session) == False:
        redirect('database/flight/timetable')
    
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `country`')
    data = cursor.fetchall()
    db.close()

    return template('country', title="Manage Country", warning="",
            data = data)

@route('/flight/addcountry')
def add_country(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/timetable')

    if check_is_admin(session) == False:
        redirect('database/flight/timetable')

    return template('addcountry', title="Add Country", warning="")

@route('/flight/addcountry', method = 'POST')
def do_add_country(session):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    name = request.forms.get('name')
    abbre = request.forms.get('abbre')
    
    if re.match("[A-Z]{3}", abbre) == None:
        return template('addcountry', title="New Country", warning="Abbre. should be 3 capital letters")
    
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `country` where abbre = %s or name = %s', (abbre, name))
    data = cursor.fetchall()
    if data == ():
        cursor.execute('insert into `country` values(0, %s, %s)', (name, abbre))
        db.commit()
        db.close()
        return template('addcountry', title="New Country", warning="Sucessfully add")
    else:
        return template('addcountry', title="New Country", warning="The country is already added")

@route('/flight/editcountry/<country_id>')
def edit_country(session, country_id):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/timetable')

    if check_is_admin(session) == False:
        redirect('database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `country` where id = %s', (country_id))
    data = cursor.fetchone()
    db.close()

    return template('editcountry', title="Edit Country", warning="",
            data = data, country_id = country_id),
        
@route('/flight/editcountry/<country_id>', method='POST')
def do_edit_country(session, country_id):
    name = request.forms.get('name')
    abbre = request.forms.get('abbre')
    data = [country_id, name, abbre]
    
    if len(abbre) != 3 or re.match("[A-Z]{3}", abbre) == None:
        return template('editcountry', title="Edit Country", warning="Abbre. should be 3 capital letters",
                data = data, country_id = country_id)
    
    db = db_login()
    cursor = db.cursor()
    cursor.execute('select * from `country` where (abbre = %s or name = %s) and id != %s', 
                            (abbre, name, country_id))
    test = cursor.fetchall()
    if test == ():
        cursor.execute('update `country` set name = %s, abbre = %s where id = %s', (name, abbre, country_id))
        db.commit()
        db.close()
        return template('editcountry', title="Edit Country", warning="Sucessfully edit",
            data = data, country_id = country_id)
    else:
        return template('editcountry', title="Edit Country", warning="The country is already exist",
            data = data, country_id = country_id)
    
@route('/flight/delcountry/<country_id>')
def del_country(session, country_id):
    user_id = session.get('user_id')
    if is_user(user_id) == False:
        session['is_signin'] = False
        return template('sorry', title="Error", warning="You're not the user now.")

    if is_signin(session) == False:
        redirect('/database/flight/timetable')

    if check_is_admin(session) == False:
        redirect('database/flight/timetable')

    db = db_login()
    cursor = db.cursor()
    cursor.execute('delete from `country` where id = %s', (country_id))
    db.commit()
    db.close()
    
    redirect('/database/flight/country')
    
@route('/flight/ticket')
def ticket(session):
    signin = is_signin(session)
    is_admin = check_is_admin(session)

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select a.name, c.name from `airport` a\
            inner join `country` as c on c.id = a.country_id order by c.name')
    depart = cursor.fetchall()

    return template('ticket', title="Ticket", warning="",
            is_round = False, query = "", times = 0, max_row = 0, 
            search = depart, data = "", signin = signin, is_admin = is_admin)

@route('/flight/ticket', method='POST')
def search_ticket(session):
    signin = is_signin(session)
    is_admin = check_is_admin(session)

    db = db_login()
    cursor = db.cursor()
    cursor.execute('select name from `airport`')
    data = cursor.fetchall()

    translate = { 'Price':'price', 'Transfer time': 'trans_time',
                  'Arrival time': 'final_date', 'Departure time': 'first_dep_date'}

    depart = request.forms.get('depart')
    dest = request.forms.get('dest')
    times = request.forms.get('times')
    orderby = translate[request.forms.get('orderby')]
    asc = request.forms.get('asc')
    is_round = request.forms.get('is_round')

    if is_round == 'on':
        is_round = True
    else:
        is_round = False

    cursor.execute('select name from `airport`')
    cursor.execute('select a.name, c.name from `airport` a\
            inner join `country` as c on c.id = a.country_id order by c.name')
    search = cursor.fetchall()
    query = ""

    if times == '0':
        if is_round:
            query = '\
select * from \
( \
select A.first_flight_num as A_first_flight_num, A.first_dep as A_first_dep, A.first_dest as A_first_dest, \
       A.first_dep_date as first_dep_date, A.first_arri_date as A_first_arri_date, \
       A.first_flight_time as A_first_flight_time,  \
       A.sec_flight_num as A_sec_flight_num, A.sec_dep as A_sec_dep, A.sec_dest as A_sec_dest, \
       A.sec_dep_date as A_sec_dep_date, A.sec_arri_date as A_sec_arri_date, \
       A.sec_flight_time as A_sec_flight_time,  \
       A.thr_flight_num as A_thr_flight_num, A.thr_dep as A_thr_dep, A.thr_dest as A_thr_dest, \
       A.thr_dep_date as A_thr_dep_date, A.thr_arri_date as A_thr_arri_date, \
       A.thr_flight_time as A_thr_flight_time,  \
       addtime(A.flight_time, B.flight_time) as flight_time, \
       addtime(A.trans_time, B.trans_time) as trans_time, \
       A.price + B.price as price, B.final_date as final_date, \
       B.first_flight_num as B_first_flight_num, B.first_dep as B_first_dep, B.first_dest as B_first_dest, \
       B.first_dep_date as B_first_dep_date, B.first_arri_date as B_first_arri_date, \
       B.first_flight_time as B_first_flight_time,  \
       B.sec_flight_num as B_sec_flight_num, B.sec_dep as B_sec_dep, B.sec_dest as B_sec_dest, \
       B.sec_dep_date as B_sec_dep_date, B.sec_arri_date as B_sec_arri_date, \
       B.sec_flight_time as B_sec_flight_time,  \
       B.thr_flight_num as B_thr_flight_num, B.thr_dep as B_thr_dep, B.thr_dest as B_thr_dest, \
       B.thr_dep_date as B_thr_dep_date, B.thr_arri_date as B_thr_arri_date, \
       B.thr_flight_time as B_thr_flight_time \
from \
( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                    convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                             convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = "%s" \
        and dest.name = "%s" \
) as A \
inner join \
( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                    convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                             convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = "%s" \
        and dest.name = "%s" \
) as B \
on A.final_date < B.first_dep_date \
) as C \
    order by %s %s' %(depart, dest, dest, depart, orderby, asc)
        else:
            query = '\
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                    convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_dest_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_dest_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, "+00:00"), \
                                             convert_tz(f.arrival_date, dest.timezone, "+00:00"))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = "%s" \
        and dest.name = "%s" \
    order by %s %s' %(depart, dest, orderby, asc)
        cursor.execute(query)

    elif times == '1':
        if is_round:
            query = "select * from \
( \
select G.first_flight_num as G_first_flight_num, G.first_dep as G_first_dep, G.first_dest as G_first_dest, \
       G.first_dep_date as first_dep_date, G.first_arri_date as G_first_arri_date, \
       G.first_flight_time as G_first_flight_time,  \
       G.sec_flight_num as G_sec_flight_num, G.sec_dep as G_sec_dep, G.sec_dest as G_sec_dest, \
       G.sec_dep_date as G_sec_dep_date, G.sec_arri_date as G_sec_arri_date, \
       G.sec_flight_time as G_sec_flight_time,  \
       G.thr_flight_num as G_thr_flight_num, G.thr_dep as G_thr_dep, G.thr_dest as G_thr_dest, \
       G.thr_dep_date as G_thr_dep_date, G.thr_arri_date as G_thr_arri_date, \
       G.thr_flight_time as G_thr_flight_time,  \
       addtime(G.flight_time, H.flight_time) as flight_time, \
       addtime(G.trans_time, H.trans_time) as trans_time, \
       G.price + H.price as price, H.final_date as final_date, \
       H.first_flight_num as H_first_flight_num, H.first_dep as H_first_dep, H.first_dest as H_first_dest, \
       H.first_dep_date as H_first_dep_date, H.first_arri_date as H_first_arri_date, \
       H.first_flight_time as H_first_flight_time,  \
       H.sec_flight_num as H_sec_flight_num, H.sec_dep as H_sec_dep, H.sec_dest as H_sec_dest, \
       H.sec_dep_date as H_sec_dep_date, H.sec_arri_date as H_sec_arri_date, \
       H.sec_flight_time as H_sec_flight_time,  \
       H.thr_flight_num as H_thr_flight_num, H.thr_dep as H_thr_dep, H.thr_dest as H_thr_dest, \
       H.thr_dep_date as H_thr_dep_date, H.thr_arri_date as H_thr_arri_date, \
       H.thr_flight_time as H_thr_flight_time \
from \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
) as G \
inner join \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
) as H \
    on G.final_date < H.first_dep_date \
) as F order by %s %s" %(depart, dest, depart, dest, dest, depart, dest, depart, orderby, asc)
        else:
            query = "select * from \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_dest_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_dest_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_dest_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
) as F order by %s %s" %(depart, dest, depart, dest, orderby, asc)
        cursor.execute(query)
    else:
        if is_round:
            query = "select * from \
( \
select G.first_flight_num as G_first_flight_num, G.first_dep as G_first_dep, G.first_dest as G_first_dest, \
       G.first_dep_date as first_dep_date, G.first_arri_date as G_first_arri_date, \
       G.first_flight_time as G_first_flight_time,  \
       G.sec_flight_num as G_sec_flight_num, G.sec_dep as G_sec_dep, G.sec_dest as G_sec_dest, \
       G.sec_dep_date as G_sec_dep_date, G.sec_arri_date as G_sec_arri_date, \
       G.sec_flight_time as G_sec_flight_time,  \
       G.thr_flight_num as G_thr_flight_num, G.thr_dep as G_thr_dep, G.thr_dest as G_thr_dest, \
       G.thr_dep_date as G_thr_dep_date, G.thr_arri_date as G_thr_arri_date, \
       G.thr_flight_time as G_thr_flight_time,  \
       addtime(G.flight_time, H.flight_time) as flight_time, \
       addtime(G.trans_time, H.trans_time) as trans_time, \
       G.price + H.price as price, H.final_date as final_date, \
       H.first_flight_num as H_first_flight_num, H.first_dep as H_first_dep, H.first_dest as H_first_dest, \
       H.first_dep_date as H_first_dep_date, H.first_arri_date as H_first_arri_date, \
       H.first_flight_time as H_first_flight_time,  \
       H.sec_flight_num as H_sec_flight_num, H.sec_dep as H_sec_dep, H.sec_dest as H_sec_dest, \
       H.sec_dep_date as H_sec_dep_date, H.sec_arri_date as H_sec_arri_date, \
       H.sec_flight_time as H_sec_flight_time,  \
       H.thr_flight_num as H_thr_flight_num, H.thr_dep as H_thr_dep, H.thr_dest as H_thr_dest, \
       H.thr_dep_date as H_thr_dep_date, H.thr_arri_date as H_thr_arri_date, \
       H.thr_flight_time as H_thr_flight_time \
from \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
    union \
    ( \
    select first_flight_num, E.first_dep , E.first_dest, E.first_dep_date, E.first_arri_date, E.first_flight_time,  \
        sec_flight_num, E.sec_dep, E.sec_dest, E.sec_dep_date, E.sec_arri_date, E.sec_flight_time, \
        thr_flight_num, E.thr_dep, E.thr_dest, E.thr_dep_date, E.thr_arri_date, E.thr_flight_time, \
        addtime(addtime(first_flight_time, sec_flight_time), thr_flight_time) as flight_time, \
        addtime(first_trans_time, sec_trans_time) as trans_time, \
        (first_price + sec_price + thr_price) * 0.8 as price, thr_arri_date as final_date \
    from \
    ( \
        select C.*, D.*, sec_to_time(timestampdiff(second, C.sec_arri_date, D.thr_dep_date)) as sec_trans_time \
        from \
        (    \
            select *, sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as first_trans_time from  \
            (    \
                select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
                        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
                           f.price as first_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dep.name = '%s' \
            )  as A \
            inner join \
            ( \
                select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                        f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, \
                       f.price as sec_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
             ) as B \
                on A.first_dest = B.sec_dep  \
                    and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
                    and B.sec_dest != '%s'  \
            ) as C \
            inner join \
            ( \
                select f.flight_number as thr_flight_num, dep.name as thr_dep, dest.name as thr_dest, \
                        f.departure_date as thr_dep_date, f.arrival_date as thr_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as thr_flight_time, \
                       f.price as thr_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dest.name = '%s' \
            ) as D \
            on C.sec_dest = D.thr_dep \
                and timestampdiff(hour, C.sec_arri_date, D.thr_dep_date) >= 2 \
        ) as E \
    ) \
) as G \
inner join \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_arri_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_arri_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
    union \
    ( \
    select first_flight_num, E.first_dep , E.first_dest, E.first_dep_date, E.first_arri_date, E.first_flight_time,  \
        sec_flight_num, E.sec_dep, E.sec_dest, E.sec_dep_date, E.sec_arri_date, E.sec_flight_time, \
        thr_flight_num, E.thr_dep, E.thr_dest, E.thr_dep_date, E.thr_arri_date, E.thr_flight_time, \
        addtime(addtime(first_flight_time, sec_flight_time), thr_flight_time) as flight_time, \
        addtime(first_trans_time, sec_trans_time) as trans_time, \
        (first_price + sec_price + thr_price) * 0.8 as price, thr_arri_date as final_date \
    from \
    ( \
        select C.*, D.*, sec_to_time(timestampdiff(second, C.sec_arri_date, D.thr_dep_date)) as sec_trans_time \
        from \
        (    \
            select *, sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as first_trans_time from  \
            (    \
                select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
                        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
                           f.price as first_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dep.name = '%s' \
            )  as A \
            inner join \
            ( \
                select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                        f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, \
                       f.price as sec_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
             ) as B \
                on A.first_dest = B.sec_dep  \
                    and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
                    and B.sec_dest != '%s'  \
            ) as C \
            inner join \
            ( \
                select f.flight_number as thr_flight_num, dep.name as thr_dep, dest.name as thr_dest, \
                        f.departure_date as thr_dep_date, f.arrival_date as thr_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as thr_flight_time, \
                       f.price as thr_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dest.name = '%s' \
            ) as D \
            on C.sec_dest = D.thr_dep \
                and timestampdiff(hour, C.sec_arri_date, D.thr_dep_date) >= 2 \
        ) as E \
    ) \
) as H \
    on G.final_date < H.first_dep_date \
) as F order by %s %s" \
    %(depart, dest, depart, dest, depart, depart, dest, dest, depart, dest, depart, dest, dest, depart, orderby, asc)
        else:
            query = "select * from \
( \
    ( \
    select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                    convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
            NULL as sec_flight_num, NULL as sec_dep, NULL as sec_dest, NULL as sec_dep_date, NULL as sec_dest_date, NULL as sec_flight_time, \
            NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_dest_date, NULL as thr_flight_time, \
        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as flight_time, \
            0 as trans_time, f.price as price, f.arrival_date as final_date \
    from flight f  \
        inner join airport as dep  \
            on dep.id = f.departure \
        join airport as dest \
            on dest.id = f.destination \
    where dep.name = '%s' \
        and dest.name = '%s' \
    ) \
    union \
    ( \
    select A.first_flight_num, A.first_dep , A.first_dest, A.first_dep_date, A.first_arri_date, A.first_flight_time,  \
        B.sec_flight_num, B.sec_dep, B.sec_dest, B.sec_dep_date, B.sec_arri_date, B.sec_flight_time, \
        NULL as thr_flight_num, NULL as thr_dep, NULL as thr_dest, NULL as thr_dep_date, NULL as thr_dest_date, NULL as thr_flight_time, \
        addtime(first_flight_time, sec_flight_time) as flight_time, \
        sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as trans_time, \
        (A.price + B.price) * 0.9 as price, B.sec_arri_date as final_date \
    from \
        ( \
        select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dep.name = '%s' \
        )  as A \
    inner join \
    ( \
        select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
            sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                 convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, f.price as price \
        from flight f  \
            inner join airport as dep \
                on dep.id = f.departure \
            join airport as dest \
                on dest.id = f.destination \
        where dest.name = '%s' \
    ) as B \
    on A.first_dest = B.sec_dep \
        and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
    ) \
    union \
    ( \
    select first_flight_num, E.first_dep , E.first_dest, E.first_dep_date, E.first_arri_date, E.first_flight_time,  \
        sec_flight_num, E.sec_dep, E.sec_dest, E.sec_dep_date, E.sec_arri_date, E.sec_flight_time, \
        thr_flight_num, E.thr_dep, E.thr_dest, E.thr_dep_date, E.thr_arri_date, E.thr_flight_time, \
        addtime(addtime(first_flight_time, sec_flight_time), thr_flight_time) as flight_time, \
        addtime(first_trans_time, sec_trans_time) as trans_time, \
        (first_price + sec_price + thr_price) * 0.8 as price, thr_arri_date as final_date \
    from \
    ( \
        select C.*, D.*, sec_to_time(timestampdiff(second, C.sec_arri_date, D.thr_dep_date)) as sec_trans_time \
        from \
        (    \
            select *, sec_to_time(timestampdiff(second, A.first_arri_date, B.sec_dep_date)) as first_trans_time from  \
            (    \
                select f.flight_number as first_flight_num, dep.name as first_dep, dest.name as first_dest, \
                            f.departure_date as first_dep_date, f.arrival_date as first_arri_date, \
                        sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                             convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as first_flight_time, \
                           f.price as first_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dep.name = '%s' \
            )  as A \
            inner join \
            ( \
                select f.flight_number as sec_flight_num, dep.name as sec_dep, dest.name as sec_dest, \
                        f.departure_date as sec_dep_date, f.arrival_date as sec_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as sec_flight_time, \
                       f.price as sec_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
             ) as B \
                on A.first_dest = B.sec_dep  \
                    and timestampdiff(hour, A.first_arri_date, B.sec_dep_date) >= 2 \
                    and B.sec_dest != '%s'  \
            ) as C \
            inner join \
            ( \
                select f.flight_number as thr_flight_num, dep.name as thr_dep, dest.name as thr_dest, \
                        f.departure_date as thr_dep_date, f.arrival_date as thr_arri_date, \
                    sec_to_time(timestampdiff(second, convert_tz(f.departure_date, dep.timezone, '+00:00'), \
                                                         convert_tz(f.arrival_date, dest.timezone, '+00:00'))) as thr_flight_time, \
                       f.price as thr_price \
                from flight f  \
                    inner join airport as dep \
                        on dep.id = f.departure \
                    join airport as dest \
                        on dest.id = f.destination \
                where dest.name = '%s' \
            ) as D \
            on C.sec_dest = D.thr_dep \
                and timestampdiff(hour, C.sec_arri_date, D.thr_dep_date) >= 2 \
        ) as E \
    ) \
) as F order by %s %s" %(depart, dest, depart, dest, depart, depart, dest, orderby, asc)
        cursor.execute(query)

    data = cursor.fetchall()
    db.close()

    rowspan_num = []
    for item in data:
        if item[7] == None:
            rowspan_num.append(1)
        elif item[13] == None:
            rowspan_num.append(2)
        else:
            rowspan_num.append(3)
        if is_round:
            if item[28] == None:
                rowspan_num.append(1)
            elif item[34] == None:
                rowspan_num.append(2)
            else:
                rowspan_num.append(3)


    return template('ticket', title="Ticket", warning="",
            times = int(times), max_row = rowspan_num, search = search, data = data, 
            is_round = is_round, query = query, signin = signin, is_admin = is_admin)
