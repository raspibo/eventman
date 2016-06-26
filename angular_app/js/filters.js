'use strict';

/* Filters for EventMan(ager) lists of objects. */

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
            if (!(data.event && data.event.persons && data.event.persons.length)) {
                return inputArray;
            }
            for (var x=0; x < data.event.persons.length; x++) {
                if (!data.includeCancelled && data.event.persons[x].cancelled) {
                    continue;
                }
                registeredIDs.push(data.event.persons[x].person_id);
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
        return function(inputArray, searchText) {
            var wordArray = searchText ? searchText.toLowerCase().split(/\s+/) : [];
            for (var x=0; x < wordArray.length; x++) {
                inputArray = $filter('filter')(inputArray, wordArray[x]);
            }
            return inputArray;
        };
    }]
);


/* Filter that returns only the (not) registered persons at an event. */
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

