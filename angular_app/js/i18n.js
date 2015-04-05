/* i18n for Event(man) */

eventManApp.config(['$translateProvider', function ($translateProvider) {
    $translateProvider.translations('it_IT', {
        'Events': 'Eventi',
        'Add event': 'Nuovo evento',
        'Persons': 'Persone',
        'Add person': 'Nuova persona',
        'Import persons': 'Importa persone',
    });
 
    $translateProvider.preferredLanguage('it_IT');
}]);
