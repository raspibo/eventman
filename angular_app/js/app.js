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
      when('/persons/:personID', {
        templateUrl: 'person-detail.html',
        controller: 'PersonDetailsCtrl'
      }).
      when('/events', {
        templateUrl: 'events-list.html',
        controller: 'EventsListCtrl'
      }).
      when('/events/:eventID', {
        templateUrl: 'event-detail.html',
        controller: 'EventDetailsCtrl'
      }).
      otherwise({
        redirectTo: '/events'
      });
}]);

