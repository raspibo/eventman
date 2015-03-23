'use strict';

/* Services that are used to interact with the backend. */
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
            get: {method: 'GET',
                transformResponse: function(data, headers) {
                    data = angular.fromJson(data);
                    if (data && data['begin-datetime']) {
                        data['begin-datetime'] = data['begin-datetime'].getTime();
                    }
                    if (data && data['end-datetime']) {
                        data['end-datetime'] = data['end-datetime'].getTime();
                    }
                    return data;
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

