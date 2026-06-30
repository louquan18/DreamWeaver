# syntax=docker/dockerfile:1.7

FROM maven:3.9-eclipse-temurin-21-alpine AS build
WORKDIR /workspace

COPY pom.xml ./
COPY src src
RUN --mount=type=cache,target=/root/.m2 mvn -B -DskipTests package

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /workspace/target/java-service-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
