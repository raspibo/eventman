'use strict';
/*
    Copyright 2015-2017 Davide Alberani <da@erlug.linux.it>
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
    'ngAnimate',
    'eventManServices',
    'eventManControllers',
    'ui.bootstrap',
    'ui.router',
    'pascalprecht.translate',
    'angularFileUpload',
    'angular-websocket',
    'eda.easyFormViewer',
    'eda.easyformGen.stepway'
]);


/* Add some utilities to the global scope. */
eventManApp.run(['$rootScope', '$state', '$stateParams', '$log', 'Info',
    function($rootScope, $state, $stateParams, $log, Info) {
        $rootScope.app_uuid = guid();
        $rootScope.info = {};
        $log.debug('App UUID: ' + $rootScope.app_uuid);
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;

        $rootScope.error = {error: false, message: '', code: 0};

        $rootScope.readInfo = function(callback) {
            Info.get({}, function(data) {
                $rootScope.info = data || {};
                if (data.authentication_required && !(data.user && data.user._id)) {
                    $state.go('login');
                } else if (callback) {
                    callback(data);
                }
            });
        };

        $rootScope.showError = function(error) {
            $rootScope.error.code = error.code;
            $rootScope.error.message = error.message;
            $rootScope.error.error = true;
        };

        $rootScope.clearError = function() {
            $rootScope.error.code = null;
            $rootScope.error.message = '';
            $rootScope.error.error = false;
        };

        $rootScope.errorHandler = function(response) {
            $log.debug('Handling error message:');
            $log.debug(response);
            $rootScope.error.status = response.status;
            $rootScope.error.statusText = response.statusText;
            if (response.data && response.data.error) {
                $rootScope.showError(response.data);
            } else {
                $rootScope.clearError();
            }
        };

        /* Check privileges of the currently logged in user or of the one specified with the second parameter. */
        $rootScope.hasPermission = function(permission, user) {
            if (!(user || ($rootScope.info && $rootScope.info.user && $rootScope.info.user.permissions))) {
                return false;
            }
            if (!user) {
                user = $rootScope.info.user;
            }
            var granted = false;
            var splitted_permission = permission.split('|');
            var global_permission = splitted_permission[0] + '|all';

            angular.forEach(user.permissions || [],
                    function(value, idx) {
                        if (value === 'admin|all' || value === global_permission || value === permission) {
                            granted = true;
                            return;
                        }
                    }
            );
            return granted;
        };

        $rootScope.readInfo();
    }]
);


/* Configure the states. */
eventManApp.config(['$stateProvider', '$urlRouterProvider', '$compileProvider',
    function($stateProvider, $urlRouterProvider, $compileProvider) {
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(https?|ftp|mailto|tel|file|blob):/);
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
            .state('event.view', {
                url: '/:id/view',
                templateUrl: 'event-edit.html',
                controller: 'EventDetailsCtrl'
            })
            .state('event.edit', {
                url: '/:id/edit',
                templateUrl: 'event-edit.html',
                controller: 'EventDetailsCtrl'
            })
            .state('event.tickets', {
                url: '/:id/tickets',
                templateUrl: 'event-tickets.html',
                controller: 'EventTicketsCtrl'
            })
            .state('event.ticket', {
                url: '/:id/ticket',
                templateUrl: 'ticket-main.html'
            })
            .state('event.ticket.new', {
                url: '/new',
                templateUrl: 'ticket-edit.html',
                controller: 'EventTicketsCtrl'
            })
            .state('event.ticket.edit', {
                url: '/:ticket_id/edit',
                templateUrl: 'ticket-edit.html',
                controller: 'EventTicketsCtrl'
            })
            .state('tickets', {
                url: '/tickets',
                templateUrl: 'tickets-list.html',
                controller: 'EventsListCtrl'
            })
            .state('import', {
                url: '/import',
                templateUrl: 'import-main.html'
            })
            .state('import.persons', {
                url: '/persons',
                templateUrl: 'import-persons.html',
                controller: 'FileUploadCtrl'
            })
            .state('users', {
                url: '/users',
                templateUrl: 'users-list.html',
                controller: 'UsersCtrl'
            })
            .state('user', {
                url: '/user',
                templateUrl: 'user-main.html'
            })
            .state('user.edit', {
                url: '/:id/edit',
                templateUrl: 'user-edit.html',
                controller: 'UsersCtrl'
            })
            .state('login', {
                url: '/login',
                templateUrl: 'login.html',
                controller: 'UsersCtrl'
            });
    }
]);

