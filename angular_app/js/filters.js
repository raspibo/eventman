'use strict';

/* Filters for EventMan(ager) lists of objects. */

/* Filter for persons (not) registered for a given event. */
eventManApp.filter('personRegistered', ['$filter',
    function($filter) {
        return function(inputArray, data) {
            if (data.present === undefined) {
                data.present = true;
            }
            inputArray = inputArray || [];
            var returnArray = [];
            var registeredIDs = [];
            if (!(data.event && data.event.tickets && data.event.tickets.length)) {
                return inputArray;
            }
            for (var x=0; x < data.event.tickets.length; x++) {
                if (!data.includeCancelled && data.event.tickets[x].cancelled) {
                    continue;
                }
                registeredIDs.push(data.event.tickets[x]._id);
            }
            for (var x=0; x < inputArray.length; x++) {
                var found = registeredIDs.indexOf(inputArray[x]._id) != -1;
                if ((found && data.present) || (!found && !data.present)) {
                    returnArray.push(inputArray[x]);
                }
            }
            return returnArray;
        }
    }]
);


/* Filter that handles splitted words. */
eventManApp.filter('splittedFilter', ['$filter',
    function($filter) {
        var negate = function(actual, expected) {
            if (expected == 'false') {
                expected = false;
            } else if (expected == 'true') {
                expected = true;
            }
            if (actual.toLowerCase) {
                actual = actual.toLowerCase();
            }
            return actual != expected;
        };
        return function(inputArray, searchText) {
            var wordArray = searchText ? searchText.toLowerCase().split(/\s+/) : [];
            var comparator = false;
            for (var x=0; x < wordArray.length; x++) {
                var filter_item = wordArray[x];
                comparator = false;
                if (!filter_item) {
                    continue;
                }
                if (filter_item.indexOf(':') != -1) {
                    if (filter_item[0] == '!') {
                        comparator = negate;
                        filter_item = filter_item.slice(1);
                    }
                    var filter_item_split = filter_item.split(':', 2);
                    filter_item = {};
                    filter_item[filter_item_split[0]] = filter_item_split[1];
                }
                inputArray = $filter('filter')(inputArray, filter_item, comparator);
            }
            return inputArray;
        };
    }]
);


/* Filter that returns only the (not) registered tickets at an event. */
eventManApp.filter('registeredFilter', ['$filter',
    function($filter) {
        return function(inputArray, data) {
            if (!data) {
                data = {};
            }
            var returnArray = [];
            for (var x=0; x < inputArray.length; x++) {
                if ((!data.onlyCancelled && !inputArray[x]['cancelled']) ||
                        (data.onlyCancelled && inputArray[x]['cancelled']) ||
                        data.all) {
                    returnArray.push(inputArray[x]);
                }
            }
            return returnArray;
        };
    }]
);


/* Filter that implements a generic pagination. */
eventManApp.filter('pagination', ['$filter',
    function($filter) {
        return function(inputArray, page, itemsPerPage) {
            var begin = (page - 1) * itemsPerPage;
            var end = begin + itemsPerPage;
            return inputArray.slice(begin, end);;
        };
    }]
);


/* Filter that returns only the attendees at an event. */
eventManApp.filter('attendeesFilter', ['$filter',
    function($filter) {
        return function(inputArray) {
            var returnArray = [];
            for (var x=0; x < inputArray.length; x++) {
                if (inputArray[x]['attended'] && !inputArray[x]['cancelled']) {
                    returnArray.push(inputArray[x]);
                }
            }
            return returnArray;
        };
    }]
);

