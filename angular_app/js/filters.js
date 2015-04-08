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

