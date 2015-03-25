'use strict';
/*
    Copyright 2015 Davide Alberani <da@erlug.linux.it>
                   RaspiBO <info@raspibo.org>

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/


String.prototype.getTime = function() {
    var ms = Date.parse(this);
    return new Date(ms);
};


/* Register our fantastic app. */
var eventManApp = angular.module('eventManApp', [
    'ngRoute',
    'eventManServices',
    'eventManControllers',
    'ui.bootstrap'
]);

//angular.module('eventManApp', ['ui.bootstrap']);


/* Directive that can be used to make an input field react to the press of Enter. */
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


/* Configure the routes. */
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
    }
]);

