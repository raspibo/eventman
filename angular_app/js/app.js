'use strict';

var eventManApp = angular.module('eventManApp', [
    'ngRoute',
    'eventManServices',
    'eventManControllers'
]);


eventManApp.directive('ngEnter', function () {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if(event.which === 13) {
                scope.$apply(function (){
                    scope.$eval(attrs.ngEnter);
                });
                event.preventDefault();
            }
        });
    };
});


eventManApp.config(['$routeProvider',
    function($routeProvider) {
        $routeProvider.
            when('/persons', {
                templateUrl: 'persons-list.html',
                controller: 'PersonsListCtrl'
            }).
            when('/persons/:id', {
                templateUrl: 'person-detail.html',
                controller: 'PersonDetailsCtrl'
            }).
            when('/events', {
                templateUrl: 'events-list.html',
                controller: 'EventsListCtrl'
            }).
            when('/events/:id', {
                templateUrl: 'event-detail.html',
                controller: 'EventDetailsCtrl'
            }).
            when('/new-event', {
                templateUrl: 'event-detail.html',
                controller: 'EventDetailsCtrl'
            }).
            when('/new-person', {
                templateUrl: 'person-detail.html',
                controller: 'PersonDetailsCtrl'
            }).
            otherwise({
                redirectTo: '/events'
            });
}]);

