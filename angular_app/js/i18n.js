/* i18n for Event(man) */



eventManApp.config(['$translateProvider', function ($translateProvider) {
    console.log($translateProvider);
    $translateProvider.useStaticFilesLoader({
        prefix: '/static/i18n/',
        suffix: '.json'
    });

    $translateProvider.useSanitizeValueStrategy('escaped');
    $translateProvider.preferredLanguage('it_IT');
    //$translateProvider.fallbackLanguage('en_US');
}]);

