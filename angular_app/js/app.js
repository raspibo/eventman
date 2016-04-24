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
    'angularFileUpload',
    'angular-websocket'
]);


/* Add some utilities to the global scope. */
eventManApp.run(['$rootScope', '$state', '$stateParams', '$log',
    function($rootScope, $state, $stateParams, $log) {
        $rootScope.app_uuid = guid();
        $log.debug('App UUID: ' + $rootScope.app_uuid);
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
    }]
);


/* Configure the states. */
eventManApp.config(['$stateProvider', '$urlRouterProvider',
    function($stateProvider, $urlRouterProvider) {
        $urlRouterProvider.otherwise('/events');
        $stateProvider
            .state('events', {
                url: '/events',
                templateUrl: 'events-list.html',
                controller: 'EventsListCtrl'
            })
            .state('event', {
                url: '/event',
                templateUrl: 'event-main.html'
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
                templateUrl: 'person-main.html'
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
                templateUrl: 'import-main.html'
            })
            .state('import.persons', {
                url: '/persons',
                templateUrl: 'import-persons.html',
                controller: 'FileUploadCtrl'
            });
    }
]);

