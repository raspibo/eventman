var eventManApp = angular.module('eventManApp', [
  'ngRoute',
  'eventManControllers'
]);

eventManApp.config(['$routeProvider',
  function($routeProvider) {
    $routeProvider.
      when('/persons', {
        templateUrl: 'persons-list.html',
        controller: 'PersonsListCtrl'
      }).
      when('/persons/:personId', {
        templateUrl: 'person-detail.html',
        controller: 'PersonDetailCtrl'
      }).
      when('/events', {
        templateUrl: 'events-list.html',
        controller: 'EventsListCtrl'
      }).
      when('/events/:eventId', {
        templateUrl: 'event-detail.html',
        controller: 'EventDetailCtrl'
      }).
      otherwise({
        redirectTo: '/events'
      });
}]);

