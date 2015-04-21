'use strict';

/* Directives for DOM manipulation and interaction. */

/* Directive that can be used to make an input field react to the press of Enter. */
eventManApp.directive('eventmanPressEnter', function () {
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

eventManApp.directive('eventmanFocus', function () {
    function link(scope, element, attrs) {
        element[0].focus();
    };
    return {
        link: link
    };
});


eventManApp.directive('resetFocus', function () {
    function link(scope, element, attrs) {
        element.on('click', function() {
            // FIXME: that's so wrong!  We need to make the new directive communicate.
            var el = angular.element(document.querySelector('#query-persons'));
            el.length && el[0].focus();
        });
    };
    return {
        link: link
    };
});


eventManApp.directive('eventmanMessage', ['$timeout',
    function($timeout) {
        function link(scope, element, attrs) {
            scope.dControl = scope.control || {};
            scope.dControl.isVisible = false;

            scope.dControl.show = function(cfg) {
                cfg = cfg || {};
                scope.dControl.isVisible = true;
                scope.dControl.message = cfg.message;
                scope.dControl.isError = cfg.isError;
                $timeout(function () {
                    scope.dControl.isVisible = false;
                }, cfg.timeout || 2000);
            };
        };

        return {
            scope: {
                control: '='
            },
            link: link,
            replace: true,
            template: '<div ng-if="dControl.isVisible">{{dControl.message}}</div>'
        };
    }]
);

