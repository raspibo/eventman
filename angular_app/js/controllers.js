'use strict';

/* Controllers */

var eventManApp = angular.module('eventManApp', []);

eventManApp.controller('PersonsListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('/persons').success(function(data) {
            $scope.persons = data.persons;
            $scope.orderProp = 'name';
        });
    }]
);

