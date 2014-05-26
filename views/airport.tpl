<!DOCTYPE html>
<html>
<head>
    <title> {{title}} </title>
    <meta charset = "utf-8" />
    <link rel="stylesheet" type="text/css" href="../static/style.css" />
</head>
<body>
    <div id="time">
        <p><a href="signout">Sign out</a></p>
        % if warning != "":
            <h3> {{warning}} </h3>
        % end
        <h1>Airport Management</h1>
    <table>
        <tr>
            <th><h4>ID</h4></th>
            <th><h4>Name</h4></th>
            <th><h4>Location</h4></th>
            <th><h4>Longitude</h4></th>
            <th><h4>Latitude</h4></th>
            <th><h4>Country</h4></th>
            <th><h4>Timezone</h4></th>
            <th><h4>Operation</h4></th>
        </tr>
        % for airport in data:
        <tr>
            % for i in xrange(7):
                <td> {{airport[i]}} </td>
            % end
            <td>
                <a href="editairport/{{airport[0]}}" type="submit" name="edit" value="{{airport[0]}}">Edit</a>
                <a href="delairport/{{airport[0]}}" type="submit" name="delete" value="{{airport[0]}}">Delete</a>
            </td>
        </tr>
        % end
    </table>
    <div id="button">
    <table>
        <tr>
            <td><a href="user"><input type="button" value="Manage user" /></a></td>
            <td><a href="timetable"><input type="button" value="Listing planes"/></a></td>
            <td></td>
            <td><a href="addairport"><input type="button" value="Add airport" /></a></td>
        </tr>
    </table>
    </div>
    </div>
</body>
</html>
