'use strict';

/* Services that are used to interact with the backend. */
var eventManServices = angular.module('eventManServices', ['ngResource']);


eventManServices.factory('Event', ['$resource',
    function($resource) {
        return $resource('events/:id', {id: '@_id', person_id: '@person_id'}, {

            all: {
                method: 'GET',
                isArray: true,
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).events;
                }
            },

            get: {method: 'GET',
                transformResponse: function(data, headers) {
                    data = angular.fromJson(data);
                    if (data && data['begin-datetime']) {
                        data['begin-date'] = data['begin-date'].getTime();
                    }
                    if (data && data['end-datetime']) {
                        data['end-date'] = data['end-date'].getTime();
                    }
                    return data;
                }
            },

            update: {method: 'PUT'},

            updatePerson: {
                method: 'PUT',
                isArray: false,
                url: 'events/:id/persons/:person_id',
                transformResponse: function(data, headers) {
                    return angular.fromJson(data);
                }
            },

            addPerson: {
                method: 'POST',
                isArray: false,
                url: 'events/:id/persons/:person_id',
                transformResponse: function(data, headers) {
                    return angular.fromJson(data);
                }
            },

            deletePerson: {
                method: 'DELETE',
                isArray: false,
                url: 'events/:_id/persons/:person_id',
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
                    return angular.fromJson(data).events;
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
                    return angular.fromJson(data).events;
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

            update: {method: 'PUT'},
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

