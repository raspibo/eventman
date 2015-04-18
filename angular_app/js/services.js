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
                isArray: true,
                url: 'events/:id/persons/:person_id',
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).event.persons;
                }
            },

            addPerson: {
                method: 'POST',
                isArray: true,
                url: 'events/:id/persons/:person_id',
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).event.persons;
                }
            },

            deletePerson: {
                method: 'DELETE',
                isArray: true,
                url: 'events/:_id/persons/:person_id',
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).event.persons;
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

