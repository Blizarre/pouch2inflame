#! /usr/bin/env node

import Readability from '@mozilla/readability';
import JSDOM from 'jsdom';
import fetch from 'node-fetch';

async function main(url) {
    const response = await fetch(url);
    var doc = new JSDOM.JSDOM(await response.text(), {
        "resources": "usable",
        url: url
    });

    let reader = new Readability.Readability(doc.window.document);

    await streamWriteAsync(process.stdout, reader.parse().content);
}


async function streamWriteAsync(stream, data) {
    return new Promise((resolve, reject) => {
        const callback = (err) => {
            if (err) {
                reject(err)
            } else {
                resolve(undefined);
            }
        };
        stream.write(data, 'utf-8', callback);
    });
}


main(process.argv[2])
    .then(() => {
        process.exit(0);
    })
    .catch(err => {
        console.error(err);
        process.exit(1);
    });
