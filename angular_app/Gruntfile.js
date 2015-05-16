'use strict';

module.exports = function(grunt) {
    grunt.initConfig({
        i18nextract: {
                default_options: {
                src: ['*.html', 'js/*.js'],
                lang: ['it_IT'],
                dest: '../static/i18n'
                }
            }
        }
    );

    grunt.loadTasks('tasks');
    grunt.loadNpmTasks('grunt-angular-translate');

    grunt.registerTask('translate', ['i18nextract']);
    grunt.registerTask('default', ['translate']);
};

