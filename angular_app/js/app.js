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

/* Register our fantastic app. */
var eventManApp = angular.module('eventManApp', [
    'ngRoute',
    'eventManServices',
    'eventManControllers',
    'ui.bootstrap',
    'ui.router',
    'pascalprecht.translate',
    'angularFileUpload'
]);


/* Add some utilities to the global scope. */
eventManApp.run(['$rootScope', '$state', '$stateParams',
    function($rootScope, $state, $stateParams) {
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
    }]
);


/* Filter that handles splitted words. */
eventManApp.filter('splittedFilter', ['$filter',
    function($filter) {
        return function(inputArray, searchText) {
            var wordArray = searchText ? searchText.toLowerCase().split(/\s+/) : [];
            for (var x=0; x < wordArray.length; x++) {
                inputArray = $filter('filter')(inputArray, wordArray[x]);
            }
            return inputArray;
        };
    }]
);


/* Filter for events that have (or not) information about a registered person. */
eventManApp.filter('eventWithPersonData', ['$filter',
    function($filter) {
        return function(inputArray, mustBePresent) {
            if (mustBePresent === undefined) {
                mustBePresent = true;
            }
            inputArray = inputArray || [];
            var returnArray = [];
            for (var x=0; x < inputArray.length; x++) {
                var found = inputArray[x].person_data && inputArray[x].person_data.person_id;
                if ((found && mustBePresent) || (!found && !mustBePresent)) {
                    returnArray.push(inputArray[x]);
                }
            }
            return returnArray;
        };
    }]
);


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


/* Configure the states. */
eventManApp.config(['$stateProvider', '$urlRouterProvider',
    function($stateProvider, $urlRouterProvider) {
        $urlRouterProvider.otherwise("/events");
        $stateProvider
            .state('events', {
                url: '/events',
                templateUrl: 'events-list.html',
                controller: 'EventsListCtrl'
            })
            .state('event', {
                url: '/event',
                templateUrl: 'event-main.html',
            })
            .state('event.new', {
                url: '/new',
                templateUrl: 'event-edit.html',
                controller: 'EventDetailsCtrl'
            })
            .state('event.edit', {
                url: '/:id/edit',
                templateUrl: 'event-edit.html',
                controller: 'EventDetailsCtrl'
            })
            .state('event.info', {
                url: '/:id',
                templateUrl: 'event-info.html',
                controller: 'EventDetailsCtrl'
            })
            .state('persons', {
                url: '/persons',
                templateUrl: 'persons-list.html',
                controller: 'PersonsListCtrl'
            })
            .state('person', {
                url: '/person',
                templateUrl: 'person-main.html',
            })
            .state('person.new', {
                url: '/new',
                templateUrl: 'person-edit.html',
                controller: 'PersonDetailsCtrl'
            })
            .state('person.edit', {
                url: '/:id/edit',
                templateUrl: 'person-edit.html',
                controller: 'PersonDetailsCtrl'
            })
            .state('person.info', {
                url: '/:id',
                templateUrl: 'person-info.html',
                controller: 'PersonDetailsCtrl'
            })
            .state('import', {
                url: '/import',
                templateUrl: 'import-main.html',
            })
            .state('import.persons', {
                url: '/persons',
                templateUrl: 'import-persons.html',
                controller: 'FileUploadCtrl'
            });
    }
]);

