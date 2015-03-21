var eventManServices = angular.module('eventManServices', ['ngResource']);

eventManServices.factory('Event', ['$resource',
  function($resource) {
    return $resource('events/:eventID', {eventID: '@eventID'}, {
      all: {
        method: 'GET',
        isArray:true,
        transformResponse: function(data, headers) {
          return angular.fromJson(data).events;
        }
      }
    });
  }]
);


eventManServices.factory('Person', ['$resource',
  function($resource) {
    return $resource('persons/:personID', {personID: '@personID'}, {
      all: {
        method: 'GET',
        isArray:true,
        transformResponse: function(data, headers) {
          return angular.fromJson(data).persons;
        }
      }
    });
  }]
);

