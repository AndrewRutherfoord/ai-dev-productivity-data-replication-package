FROM node:lts

WORKDIR /app/frontend

COPY ./frontend/package.json ./frontend/yarn.lock ./
RUN yarn install

COPY ./frontend .

COPY README.md ..

CMD ["yarn", "run", "dev", "--host", "0.0.0.0"]