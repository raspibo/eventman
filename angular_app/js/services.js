'use strict';

/* Services that are used to interact with the backend. */
var eventManServices = angular.module('eventManServices', ['ngResource']);


/* Modify, in place, an object to convert datetime. */
function convert_dates(obj) {
    if (obj['begin-date']) {
        obj['begin-date'] = obj['begin_date'] = obj['begin-date'].getTime();
    }
    if (obj['end-date']) {
        obj['end-date'] = obj['end_date'] = obj['end-date'].getTime();
    }
    return obj;
}


eventManServices.factory('Event', ['$resource', '$rootScope',
    function($resource, $rootScope) {
        return $resource('events/:id', {id: '@_id', person_id: '@person_id'}, {

            all: {
                method: 'GET',
                isArray: true,
                transformResponse: function(data, headers) {
                    data = angular.fromJson(data);
                    angular.forEach(data.events || [], function(event_, event_idx) {
                        convert_dates(event_);
                    });
                    return data.events;
                }
            },

            get: {method: 'GET',
                transformResponse: function(data, headers) {
                    data = angular.fromJson(data);
                    convert_dates(data);
                    // strip empty keys.
                    angular.forEach(data.persons || [], function(person, person_idx) {
                        angular.forEach(person, function(value, key) {
                            if (value === "") {
                                delete person[key];
                            }
                        });
                    });
                    return data;
                }
            },

            update: {method: 'PUT'},

            updatePerson: {
                method: 'PUT',
                isArray: false,
                url: 'events/:id/persons/:person_id',
                params: {uuid: $rootScope.app_uuid},
                transformResponse: function(data, headers) {
                    return angular.fromJson(data);
                }
            },

            addPerson: {
                method: 'POST',
                isArray: false,
                url: 'events/:id/persons/:person_id',
                params: {uuid: $rootScope.app_uuid},
                transformResponse: function(data, headers) {
                    return angular.fromJson(data);
                }
            },

            deletePerson: {
                method: 'DELETE',
                isArray: false,
                url: 'events/:_id/persons/:person_id',
                params: {uuid: $rootScope.app_uuid},
                transformResponse: function(data, headers) {
                    return angular.fromJson(data);
                }
            }
        });
    }]
);


eventManServices.factory('Person', ['$resource',
    function($resource) {
        return $resource('persons/:id', {id: '@_id'}, {

            all: {
                method: 'GET',
                isArray: true,
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).persons;
                }
            },

            update: {method: 'PUT'},

            getEvents: {
                method: 'GET',
                url: 'persons/:_id/events',
                isArray: true,
                transformResponse: function(data, headers) {
                    data = angular.fromJson(data);
                    angular.forEach(data.events || [], function(event_, event_idx) {
                        convert_dates(event_);
                    });
                    return data.events;
                }
            }
        });
    }]
);


eventManServices.factory('Setting', ['$resource',
    function($resource) {
        return $resource('settings/', {}, {

            query: {
                method: 'GET',
                isArray: true,
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).settings;
                }
            },

            update: {method: 'PUT'}
        });
    }]
);


/* WebSocket collection used to update the list of persons of an Event. */
eventManApp.factory('EventUpdates', ['$websocket', '$location', '$log',
    function($websocket, $location, $log) {

        var dataStream = null;

        var data = {};

        var methods = {
            data: data,
            close: function() {
                $log.debug('close WebSocket connection');
                dataStream.close();
            },
            open: function() {
                $log.debug('open WebSocket connection');
                dataStream && dataStream.close();
                var proto = $location.protocol() == 'https' ? 'wss' : 'ws';
                dataStream = $websocket(proto + '://' + $location.host() + ':' + $location.port() +
                                    '/ws/' + $location.path() + '/updates');
                dataStream.onMessage(function(message) {
                    $log.debug('EventUpdates message received');
                    data.update = angular.fromJson(message.data);
                });
            }
        };

        return methods;
    }]
);

