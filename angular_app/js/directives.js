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
            var el = angular.element(document.querySelector('#query-persons'));
            el.length && el[0].focus();
        });
    };
    return {
        link: link
    };
});

