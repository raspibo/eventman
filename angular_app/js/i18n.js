eventManApp.config(['$translateProvider', function ($translateProvider) {
    $translateProvider.translations('it_IT', {
        'Events': 'Eventi',
        'Add Event': 'Nuovo evento',
        'Persons': 'Persone',
        'Add Person': 'Nuova persona',
    });
 
    $translateProvider.preferredLanguage('it_IT');
}]);
