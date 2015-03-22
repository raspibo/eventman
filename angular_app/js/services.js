'use strict';

/* Services. */
var eventManServices = angular.module('eventManServices', ['ngResource']);


eventManServices.factory('Event', ['$resource',
    function($resource) {
        return $resource('events/:id', {id: '@_id'}, {
            all: {
                method: 'GET',
                isArray: true,
                transformResponse: function(data, headers) {
                    return angular.fromJson(data).events;
                }
            },
            update: {method: 'PUT'}
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
            update: {method: 'PUT'}
        });
    }]
);

